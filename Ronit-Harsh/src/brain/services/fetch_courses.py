import requests
import re


def fetch_grades(jsession_id: str):
    """
    jsession_id example:
    A1B2C3D4E5F6F7G8H9
    """

    session = requests.Session()

    # Static cookies + dynamic JSESSIONID
    cookie = (
        f"JSESSIONID={jsession_id}; "
        "_ga_V29CTEMEGK=GS1.1.1738039295.3.1.1738039381.0.0.0; "
        "_ga=GA1.1.1963540122.1717255739; "
        "_ga_5RLMNF50VN=GS2.1.s1768818761$o35$g1$t1768818767$j54$l0$h0"
    )

    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://aims.iith.ac.in/",
        "Connection": "keep-alive"
    }

    # --------------------------------------------------
    # 1️⃣ Fetch course history page
    # --------------------------------------------------
    url1 = "https://aims.iith.ac.in/aims/courseReg/myCrsHistoryPage"

    r1 = session.get(url1, headers=headers, timeout=15)

    if r1.status_code != 200:
        raise Exception("Failed to load course history page")

    html = r1.text

    # --------------------------------------------------
    # 2️⃣ Extract student ID
    # --------------------------------------------------
    # var studentId = "USERID";
    # var studentId = “USERID”;
    match = re.search(
        r'var\s+studentId\s*=\s*[“"]([^”"]+)[”"]',
        html
    )

    if not match:
        raise Exception("Student ID not found — invalid or expired JSESSIONID")

    student_id = match.group(1)

    # --------------------------------------------------
    # 3️⃣ Fetch grades JSON
    # --------------------------------------------------
    url2 = (
        "https://aims.iith.ac.in/aims/courseReg/loadMyCoursesHistroy"
        f"?studentId={student_id}"
        "&courseCd="
        "&courseName="
        "&orderBy=1"
        "&degreeIds="
        "&acadPeriodIds="
        "&regTypeIds="
        "&gradeIds="
        "&resultIds="
        "&isGradeIds="
    )

    r2 = session.get(url2, headers=headers, timeout=15)

    if r2.status_code != 200:
        raise Exception("Failed to fetch grade data")

    return r2.json()


print(fetch_grades("63089773B88CF195C6B11EC1C443A148"))