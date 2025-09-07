from openai import OpenAI
import os
import scraper as scraper

from jinja2 import Environment, FileSystemLoader
import subprocess
import tempfile
import os
import ast
import pathlib

#TODO get api key from a config file
def generateCoverLetter(jobDetail: dict, resume: str) -> dict:
    client = OpenAI(
        api_key= os.environ.get("OPENAI_API_KEY")
    )    
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": ('Write a cover letter tailored to the job description and the resume in the input.'
                            'Return the answer using the following python dict format:'
                            '{'
                            '"Title":"title of the cover letter",'
                            '"Paragraphs":["paragraph1","paragraph2","paragraph3",...]'
                            '}'
                            'Do not include salutation and signature. Only return body paragraphs and title of the cover letter.')
            },{
                "role": "user",
                "content": f"Job description: {str(jobDetail)}. Resume:{resume}"
            }
        ]
    )
    
    return ast.literal_eval(response.choices[0].message.content)

def generateImproveCoverLetter(coverLetter, userFeedback) -> dict:
    client = OpenAI(
        api_key= os.environ.get("OPENAI_API_KEY")
    )
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": (f"Improve the following cover letter according to user's feedback: {str(coverLetter)}"
                            'Return the answer using the following python dict format:'
                            '{'
                            '"Title":"title of the cover letter",'
                            '"Paragraphs":["paragraph1","paragraph2","paragraph3",...]'
                            '}'
                            'Do not include salutation and signature. Only return body paragraphs and title of the cover letter.')
            },{
                "role": "user",
                "content": f"User feedback: {userFeedback}"
            }
        ]
    )

    return ast.literal_eval(response.choices[0].message.content)


def generateEmail(jobDescription, resume) -> dict:
    client = OpenAI(
        api_key= os.environ.get("OPENAI_API_KEY")
    )
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": ('Write a professional email to the hiring manager based on the job description and resume provided by user.'
                            'Return the result in the following python dict format:'
                            '{'
                            '"Subject": "email subject", '
                            '"Body": "email body"'
                            '}'
                            'Only include json in the response.')
            },{
                "role": "user",
                "content":f"Job description: {jobDescription}. Resume: {resume}"
            }
        ]
    )

    return ast.literal_eval(response.choices[0].message.content)

# TODO comfirm personal details with user and ask user to enter missing info
def extractUserInfo(resume: str) -> dict:
    client = OpenAI(
        api_key= os.environ.get("OPEN_API_KEY")
    )
    response = client.chat.completions.create(
        model = "gpt-4.1",
        messages=[
            {
                "role":"system",
                "content": ('Extract the follwing information from the resume provided by user: first name, last name, address, city, email, phone number'
                            'Return the result in the following python dict format and preserve appropriate capitlization for names, city, street names, etc:'
                            '{'
                            '"ApplicantFirstName": "first name", '
                            '"ApplicantLastName": "last name", '
                            '"UserAddress": "user address",'
                            '"UserCity": "user city",'
                            '"PhoneNumber": "(123) 456-7890",'
                            '"Email": "your.name@gmail.com"'
                            '}'
                            'Only include json in the response. If you cannot find any information for a key in the resume, leave the value empty')
            },{
                "role":"user",
                "content":f"resume: {resume}"
            }
        ]
    )

    return ast.literal_eval(response.choices[0].message.content)

# type of all parameters are dict
def fillTemplate(jobDetail: dict, coverLetter: dict, userInfo: dict, templatePath: str):
    env = Environment(
        loader=FileSystemLoader(templatePath),
        block_start_string='(%',
        block_end_string='%)',
        variable_start_string='((',
        variable_end_string='))',
        comment_start_string='(#',
        comment_end_string='#)',
    )
    env.filters["escapeLatex"] = escapeLatex
    template = env.get_template("coverLetterTemplate.jinja")

    formattedCoverLetter = {**jobDetail, **coverLetter, **userInfo}
    renderedTemplate =  template.render(formattedCoverLetter)
    
    return renderedTemplate

def latexToPDF(latex_code):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = f"{tmpdir}/coverLetter.tex"
        pdf_path = f"{tmpdir}/coverLetter.pdf"

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)
        
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path],
            cwd=tmpdir,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    
    return pdf_bytes

def escapeLatex(text):
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


import json
if __name__ == "__main__":

    with open (r"coverLetter\jobDescription\jobDescriptionHtml\Autonomous Network Fabric Eng_417217.txt", "r") as rawJobDescriptionFile:
        rawJobDescription = rawJobDescriptionFile.read()
        jobDetail = scraper.extractJobDetail(rawJobDescription, 123456)

        with open(r"temp\formattedCoverLetter.txt", "r") as formattedCoverLetterTxt:
            formattedCoverLetterDict = json.loads(formattedCoverLetterTxt.read())
            userInfo = {
                "ApplicantFirstName":"Bowen",
                "ApplicantLastName": "Dai"
            }
            tex = fillTemplate(jobDetail= jobDetail, coverLetter = formattedCoverLetterDict, userInfo = userInfo,templatePath="templates")
            with open(r"temp\new.pdf",'wb') as f:
                f.write(latexToPDF(tex))