from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

import requests
import json
import re
from bs4 import BeautifulSoup

from pathlib import Path

import asyncio
# for terminal to display special char
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# TODO what if the user does not have chrome?
def createSession():
    return requests.Session()

def createChromeDriver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def quitDriver(driver):
    driver.quit()

def getVerificationCode(username, password, driver):
    driver.get("https://waterlooworks.uwaterloo.ca/home.htm")

    wait = WebDriverWait(driver, 300) #wait up to 5 min

    element = driver.find_element(By.LINK_TEXT, "Students/Alumni/Staff")
    driver.execute_script("arguments[0].scrollIntoView(true);", element)

    #login
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Students/Alumni/Staff"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "userNameInput"))).send_keys(username)
    wait.until(EC.element_to_be_clickable((By.ID, "nextButton"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "passwordInput"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "submitButton"))).click()
    wait.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'verification-code')]")))
    return driver.find_element(By.XPATH, "//div[contains(@class,'verification-code')]").text

def getCookie(driver):
    wait = WebDriverWait(driver, 300)

    wait.until(EC.element_to_be_clickable((By.ID, "dont-trust-browser-button"))).click()
    wait.until(EC.url_contains("dashboard"))

    driver.get("https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm")
    cookies = driver.get_cookies()
    return cookies

def setCookies(cookies, session):
    for c in cookies:
        session.cookies.set(c['name'], c['value'])    

def getRawTokenHtml(session):
    getTokenHeaders = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Host": "waterlooworks.uwaterloo.ca",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Referer": "https://waterlooworks.uwaterloo.ca/myAccount/co-op/student.htm"
    }
    return session.get("https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm", headers=getTokenHeaders, cookies = session.cookies).text

# TODO get job id list for a folder
def getJobIDList(rawTokenHtml, session, folderValue=[]):
    bsParser = BeautifulSoup(rawTokenHtml, "html.parser")
    scripts = bsParser.find_all("script")
    jobIDToken = ''
    for s in scripts:
        if "dataParams" in s.text:
            jobIDToken = re.search(r"dataParams\s*:\s*{\s*action\s*:\s*'(.*)',", s.text).group(1)
    
    jobIDHeaders = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm",
        "Origin": "https://waterlooworks.uwaterloo.ca"
    }

    defaultItemPerPage = 50
    jobIDData = {
        "page": 1,
        "sort": json.dumps([{"key": "Id", "direction": "desc"}, {"folderId":{"type":"options","value":folderValue}}]),
        "itemsPerPage": defaultItemPerPage,
        "filters": json.dumps({"folderId":{"type":"options","value":folderValue}}),
        "columns": json.dumps([
            {"title": "Term", "key": "Term", "isId": False, "sortable": False, "visible": True},
            {"title": "ID", "key": "Id", "isId": True, "sortable": True, "visible": True},
            {"title": "Job Title", "key": "JobTitle", "isId": False, "sortable": True, "visible": True, "tableColWidth": 325,
            "dataVisualizer": {"template": "#jobTitleDataVisualizer", "mixins": [{"props": {}}], "computed": {}}},
            {"title": "Organization", "key": "Organization", "isId": False, "sortable": True, "visible": True, "tableColWidth": 225},
            {"title": "Division", "key": "Division", "isId": False, "sortable": True, "visible": True, "tableColWidth": 225},
            {"title": "Openings", "key": "Openings", "isId": False, "sortable": True, "visible": True},
            {"title": "City", "key": "City", "isId": False, "sortable": True, "visible": True},
            {"title": "Level", "key": "Level", "isId": False, "sortable": True, "visible": True},
            {"title": "App Deadline", "key": "Deadline", "isId": False, "sortable": True, "visible": True}
        ]),
        "keyword": "",
        "action": jobIDToken,
        "isDataViewer": "true"
    }
    jobIDResponse = session.post("https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm", headers=jobIDHeaders, data=jobIDData).json()

    totalResults = jobIDResponse["totalResults"]
    if(totalResults>defaultItemPerPage):
        jobIDData["itemsPerPage"] = totalResults
        jobIDResponse = session.post("https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm", headers=jobIDHeaders, data=jobIDData).json()

    IDList = list()
    for d in jobIDResponse["data"]:
        IDList.append(d["id"])
    return IDList

def getJobDetailToken(rawTokenHtml):
    bsParser = BeautifulSoup(rawTokenHtml, "html.parser")
    scripts = bsParser.find_all("script")        
    for s in scripts:
        if "getPostingOverview" in s.text:
            return re.search(r"function\s+getPostingOverview\s*\([\w\s,]*\)\s*{[^}]*?\$\.post\([^,]+,\s*{\s*action:\s*['\"]([^'\"]+)",s.text).group(1)

def getFolderOption(rawTokenHtml, folderName):
    bsParser = BeautifulSoup(rawTokenHtml, "html.parser")
    scripts = bsParser.find_all("script")
    for s in scripts:
        if "dataViewerRoot" in s.text:
            folderListStr = re.search(r"folderOptions\s*:\s*(\[[^\]]*\])", s.text).group(1)
            folderList = json.loads(folderListStr)
            for f in folderList:
                if(f["label"] == folderName):
                    return int(f["value"])

# return txt of the job description
def getJobDetail(jobID, jobDetailToken, session):
    jobDetailHeaders = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm",
    "Origin": "https://waterlooworks.uwaterloo.ca",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
    }

    jobDetailData = {
        "action": jobDetailToken,
        "postingId":jobID
    }
    
    return session.post("https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm", headers=jobDetailHeaders, data = jobDetailData).content.decode("latin1")

# TODO: any better way to know job ID? get it from the name of the file???
def extractJobDetail(rawHtml, jobID):
    rawHtml = rawHtml.replace('\r\n', '\n').replace('\r', '\n')
    soup = BeautifulSoup(rawHtml, 'html.parser')
    jobDetail = dict()
    jobDetail["id"] = jobID

    # remove tags and replace <br> with newline
    for tag in soup(['strong', 'em', 'b', 'i']):
        tag.unwrap()
    for br in soup.find_all('br'):
        br.replace_with('\n')

    for span in soup.find_all('span'):
        if 'Job Title' in span.text:
            jobDetail["Job Title"] = span.find_next_sibling('p').text.strip()
        elif 'Job Responsibilities' in span.text:
            jobDetail["Job Responsibilities"] = span.find_next_sibling('p').text.strip()
        elif 'Required Skills' in span.text:
            jobDetail["Required Skills"] = span.find_next_sibling('p').text.strip()
        
        elif 'Level' in span.text:
            p_tag = span.find_next_sibling('p')
            if p_tag:
                td_tag = p_tag.find_all('td')
                jobDetail["Level"] = [td.get_text(strip = True) for td in td_tag]

        elif 'Organization' in span.text:
            jobDetail["Company"] = span.find_next_sibling('p').text.strip()
        elif 'Division' in span.text:
            jobDetail["Division"] = span.find_next_sibling('p').text.strip()

        elif "Job - Country" in span.text:
            jobDetail["Job - Country"] = span.find_next_sibling('p').text.strip()
        elif r'Job - Province/State' in span.text:
            jobDetail["CompanyProvince"] = span.find_next_sibling('p').text.strip()
        elif "Job - City" in span.text:
            jobDetail["CompanyCity"] = span.find_next_sibling('p').text.strip()
        elif "Job - Address Line One" in span.text:
            jobDetail["CompanyAddress"] = span.find_next_sibling('p').text.strip()
        elif "Job - Postal/Zip Code" in span.text:
            jobDetail["PostalCode"] = span.find_next_sibling('p').text.strip()
            
        elif 'Application Deadline' in span.text:
            jobDetail["Application Deadline"] = re.sub(r'\s+', ' ', span.find_next_sibling('p').text.strip())
        elif 'Application Delivery' in span.text:
            applicationMethod = span.find_next_sibling('p').text.strip()
            if "website" in applicationMethod:
                jobDetail["Application Delivery"] = "Website"
            elif "email" in applicationMethod:
                jobDetail["Application Delivery"] = "Email"
            else:
                jobDetail["Application Delivery"] = applicationMethod
        elif "If By Website, Go To:" in span.text:
            jobDetail["Application Detail"] = span.find_next_sibling('p').text.strip()
        elif "If By Email, Send To:" in span.text:
            p_tag = span.find_next_sibling('p')
            if p_tag:
                button = p_tag.find('button')
                if button:
                    jobDetail["Application Detail"] = button.text.strip()
        # Is there any other application delivery than website and email? How to verify it?
        elif "If By" in span.text:
            jobDetail["Application Detail"] = span.find_next_sibling('p').text.strip()

    return jobDetail

# Assuming:
# all cover letters are in the folder "coverLetter" 
# the file name of the cover letter will be the job id
# jobID is str (test if int works?)
def uploadCoverLetter(driver, jobId):
    # open upload page
    driver.get("https://waterlooworks.uwaterloo.ca/myAccount/co-op/full/documents.htm")
    wait = WebDriverWait(driver, 300) #wait up to 5 min

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Upload A Document"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "docName"))).send_keys(jobId)
    Select(driver.find_element(By.ID, "docType")).select_by_visible_text("Cover Letter - .pdf")
    coverLetterPath = Path.cwd() / "coverLetter" / f"{jobId}.pdf"
    driver.find_element(By.ID, "fileUpload_docUpload").send_keys(str(coverLetterPath))

    wait.until(EC.text_to_be_present_in_element((By.ID, "fileLink_docUpload"), f"{jobId}.pdf"))
    driver.execute_script("document.getElementById('fileUploadForm').submit();")

# TODO handle positions that requires other document
# TODO generate resume for each position
# assuming the resume name is unique
def uploadApplicationPackage(driver, jobId, resumeName):
    driver.get("https://waterlooworks.uwaterloo.ca/myAccount/co-op/full/documents.htm")
    wait = WebDriverWait(driver, 300)

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Create An Application Package"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "name"))).send_keys(jobId)
    # select resume according to resumeName resume id: 67
    Select(driver.find_element(By.ID, "67")).select_by_visible_text(resumeName)
    # select newest grade report
    gradeReportSelect = Select(driver.find_element(By.ID, "71"))
    gradeReportIndex = len(gradeReportSelect.options) - 1
    gradeReportSelect.select_by_index(gradeReportIndex)
    # select newest work history
    workHistorySelect = Select(driver.find_element(By.ID, "76"))
    workHistoryIndex = len(workHistorySelect.options) - 1
    workHistorySelect.select_by_index(workHistoryIndex)
    # select cover letter according to cover letter name (jobID)
    Select(driver.find_element(By.ID, "66")).select_by_visible_text(jobId)

    driver.execute_script("document.getElementById('savePackageForm').submit()")
    
# TODO apply the position using the applicatioin package
# TODO only get jobId from a saved job folder

if __name__ == "__main__":
    
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options = options)

    session = createSession()
    print(getVerificationCode("waterlooEmail", "password", driver))
    print(getCookie(driver))
    #setCookies(getCookie("waterlooEmail", "password", driver), session)
    
    
    """
    rawToken = getRawTokenHtml(session)
    testFolder = getFolderOption(rawToken, "test")
    test2Folder = getFolderOption(rawToken, "test2")

    print(getJobIDList(rawTokenHtml=rawToken, session=session, folderValue=[testFolder]))
    
    uploadApplicationPackage(driver, "417355", "defaultTest")
    
    uploadCoverLetter(driver, "417355")
    
    rawToken = getRawTokenHtml(session)
    with open("rawToken.txt", 'w') as f:
        f.write(rawToken)
    
    jobIDList = getJobIDList(rawToken)
    jobDetailToken = getJobDetailToken(rawToken)
    jobDetail = getJobDetail(jobIDList[0], jobDetailToken, session)
    print(type(jobIDList))
    print(type(jobIDList[0]))
    print(jobIDList[0])
    

    with open(r"rawHTML\Fermentation_BioProcess R&D Co-op_425115.txt", 'r', encoding="latin1") as f:
        applyByEmail = f.read()
        pprint.pprint(extractJobDetail(applyByEmail, "425115"))

    with open(r"rawHTML\Web Portal Developer_416688.txt", 'r', encoding = "latin1") as f:
        applyByWebsite = f.read()
        pprint.pprint(extractJobDetail(applyByWebsite, "416688"))

    with open(r"rawHtml\Intern, Finance (SAP S_4HANA)_425580.txt", 'r', encoding = "latin1") as f:
        specialChar = f.read()
        pprint.pprint(extractJobDetail(specialChar, "425580"))
    """
    
    driver.quit()