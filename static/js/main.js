function textareaAutoSize(){
    const inputs = document.querySelectorAll("textarea");
    if (!inputs) return;
    inputs.forEach(input =>{
        const resize = () => {
            input.style.height = "auto";
            input.style.height = input.scrollHeight + "px";
        };

        resize();
        input.addEventListener("input", resize);
    });
}

function enableArrowNavigation(){
    document.addEventListener("keydown", function(e){
        if(e.key == "ArrowLeft"){
            const prev = document.getElementById("prev");
            if(prev){
                window.location.href = prev.href;
            }
        }
        if(e.key == "ArrowRight"){
            const next = document.getElementById("next");
            if(next){
                window.location.href = next.href;
            }
        }
    });
}


function enableEnterNavigation(){
    document.addEventListener("keydown", function(e){
        const inputs = Array.from(document.querySelectorAll("input, textarea"));
        const active = document.activeElement;
        const idx = inputs.indexOf(active);
        if (e.key === "Enter") {
            if (idx > -1 && idx < inputs.length - 1) {
                inputs[idx + 1].focus();
                e.preventDefault();
            }
        }
        if(e.key === "Escape"){
            active.blur();
        }
        if(e.key === "Enter" && e.shiftKey && idx > 0){
            inputs[idx - 1].focus();
            e.preventDefault();
        }
    });
}

document.addEventListener("DOMContentLoaded", ()=>{
    textareaAutoSize();
    enableArrowNavigation();
    enableEnterNavigation();
})