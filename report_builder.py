import os
import datetime
import re

import requests


# report components
HEADER = "# Report for {company}.\n{fullname} <{email}> {time}\n"

TOTAL_TASKS = "Total tasks: {total_tasks}\n"
TOTAL_CURRENT_TASKS = "\n## Current tasks ({cur_total}):\n"
TOTAL_COMPLETED_TASKS = "\n## Completed tasks ({comp_total}):\n"


TODOS_URL = "https://json.medrocket.ru/todos"
USERS_URL = "https://json.medrocket.ru/users"

def get_users() -> list:
    """Gets page with user objects on demand"""

    page_num = 1

    while(True):
        page = requests.get(USERS_URL, params={"_page":page_num})

        if(page.status_code != 200):
            page.raise_for_status()

        if(page.json() == []):
            break

        page_num += 1
        yield page.json()

def get_todos(user_id: int) -> list: 
    """Gets page with todo objects on demand"""

    page_num = 1

    while(True):
        page = requests.get(TODOS_URL, params={"userId":user_id, "_page":page_num})

        if(page.status_code != 200):
            page.raise_for_status()

        if(page.json() == []):
            break

        page_num += 1
        yield page.json()


# 1. Finds date in report file via regex
# 2. Formats date and returns formatted string
def get_date(path: str) -> str:
    """Gets creation date from report file"""

    re_exp = ("(?P<day>[0-9]{2}).(?P<month>[0-9]{2}).(?P<year>[0-9]{4})" 
              " (?P<hour>[0-9][0-9]):(?P<minute>[0-9][0-9])")

    date_format = "{year}-{month}-{day}T{hour}:{minute}" # THIS LINE

    with open(path, "r", encoding="utf-8") as file:
        data = file.read()
        match = re.search(re_exp, data)
        if match:
            return date_format.format(
                year=match.group("year"),
                month=match.group("month"),
                day=match.group("day"),
                hour=match.group("hour"),
                minute=match.group("minute"),
            )
        return 0


def validate_user(user: dict) -> bool:
    """Checks if user object has all required fields"""

    try:
        company = user["company"]["name"]
        fullname = user["name"]
        email = user["email"]
    except KeyError:
        print("User object is malformed")
        return False
    return True

def validate_todo(todo: dict) -> bool: 
    """Checks if todo object has all required fields"""

    try:
        title = todo["title"]
        completed = todo["completed"]
    except KeyError:
        print("ToDo object is malformed")
        return False

    return True

# opens file right after its creation and compares to previously formatted report
def validate_file(file_path: str, report: str):  
    """Validates if report was written successfully.

    If file write of report was successful returns True, otherwise returns False
    If there is no such file - return None
    """

    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            report_file = file.read()
            return report_file == report

    return None

# puts every user's tasks in report components with required formatting
# if there is no tasks for user returns None
def create_report(user: dict) -> str:
    """Creates report string.

    Puts every data field from user and user's todos 
    into predefined templates
    """

    company = user["company"]["name"]
    fullname = user["name"]
    email = user["email"]

    time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    cur_tasks = ""
    comp_tasks = ""

    cur_total = 0
    comp_total = 0
    
    for page in get_todos(user["id"]):
        for task in page:
            if validate_todo(task):
                if len(task["title"])>46:
                        task["title"] = task["title"][:46] + "..."
                if task["completed"] == False:
                    cur_tasks += "- " + task["title"] + "\n"
                    cur_total += 1
                elif task["completed"] == True:
                    comp_tasks += "- " + task["title"] + "\n"
                    comp_total += 1

    total_tasks = cur_total + comp_total

    report = (
        HEADER.format(company=company, fullname=fullname, email=email, time=time)
        + TOTAL_TASKS.format(total_tasks=total_tasks)
        + TOTAL_CURRENT_TASKS.format(cur_total=cur_total)
        + cur_tasks
        + TOTAL_COMPLETED_TASKS.format(comp_total=comp_total)
        + comp_tasks
        ) 
    
    if total_tasks == 0:
        return None

    return report 


def create_filename(username: str, *, date: str = None) -> str:
    """Creates filename for *username*'s report """

    if date == None:
        return f"{username}.txt"
    return f"old_{username}_{date}.txt"


def save_report(report: str, username: str) -> None:
    """Saves report to a file if no issues occured.

    If current report is malformed, this function deletes it,
    finds the most recent report file and reassigns its name
    to be the relevant one, if no recent report files are found 
    just delete the malformed one
    """

    report_path = "tasks/" + create_filename(username)

    # check if file already exists
    # if exists - rename it 
    if os.path.isfile(report_path):
        date = get_date(report_path)
        new_path = "tasks/" + create_filename(username, date=date)
        os.rename(report_path, new_path)
    
    try:
        with open(report_path, "w", encoding="utf-8") as rep_file:
            rep_file.write(report)   
    except Exception:
        print(f"Error occured while writing to file {report_path}")
    finally:
        file_is_valid = validate_file(report_path, report)
        if file_is_valid != True: 
            if file_is_valid == False:
                os.remove(report_path) 
            last_report = get_last_report(username)
            if last_report != None:                    
                os.rename("tasks/"+last_report, report_path) 


def get_last_report(username: str) -> str: #change uA789 after completion
    """Gets the last report's filename for *username*, if report exists.

    If there is a report for *username* that has been created recently, 
    this function gets its filename and returns it. If there is no previously
    created reports for that *username* - return None.
    """

    file_names = os.listdir("tasks/")

    re_exp = (f"old_{username}_(?P<year>[0-9]{{4}})-"
    "(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    "T(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}).txt")

    today = datetime.datetime.now()
    min_dif = None
    last_report = None

    for file_name in file_names:
        match = re.match(re_exp, file_name)

        if match:
            year = int( match.group("year"))
            month = int( match.group("month"))
            day = int( match.group("day"))
            hour = int( match.group("hour"))
            minute = int( match.group("minute"))

            file_date = datetime.datetime(
                year=year, 
                month=month, 
                day=day, 
                hour=hour, 
                minute=minute,)

            diff = today - file_date

            if(min_dif == None):
                min_dif = diff
                last_report = file_name

            if(diff < min_dif):
                min_dif = diff
                last_report = file_name
    
    return last_report



if __name__ == "__main__":

    dir = os.path.join(os.curdir, "tasks")
    if not os.path.exists(dir):
        os.makedirs(dir)

    for page in get_users():
        for user in page:
            if not validate_user(user):
                print(user["username"], " doesn't have required")
                continue 
            report = create_report(user)
            if report == None:
                print(user["username"], " doesn't have todos")
            else:
                username = user["username"].replace("/", "(f_slash)")
                save_report(report, username)