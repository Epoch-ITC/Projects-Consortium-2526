import re
from bs4 import BeautifulSoup

def clean_email_body(html_content: str) -> str:
    """
    Cleans email HTML content to extract plain text.
    Also strips specific footers.
    """
    if not html_content:
        return ""
    
    #HTML to Text
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n")
    
    #Disclaimer Removal
    # "Disclaimer:- This footer text is to convey that this email is sent by one of the users of IITH. So, do not mark it as SPAM."
    # We use a loose regex to catch slight variations or newlines
    disclaimer_pattern = re.compile(
        r"Disclaimer:-\s*This footer text is to convey that this email is sent by one of the users of IITH.*SPAM\.",
        re.IGNORECASE | re.DOTALL
    )
    text = disclaimer_pattern.sub("", text)
    
    # 3. Collapse extra whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    
    return text

