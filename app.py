import os
import json
import time
import config
import requests
import cssselect
import threading

from os import path
from lxml import html
from datetime import datetime


def parse_html(url, starting_link, title_selector, link_selector):
    # verify=False ignores ssl certificate
    # problems. it uses http instead of https
    response = requests.get(url, verify=False)
    status_code = response.status_code

    announcements = []
    if status_code == 200:
        content = str(response.content, 'utf-8')

        tree = html.fromstring(content)
        titles = tree.cssselect(title_selector)

        if link_selector != '':
            links = tree.cssselect(link_selector)

        for i in range(0, len(titles)):
            if i == 10:
                break

            if link_selector != '':
                link = f"{starting_link}{links[i].attrib['href']}"
            else:
                link = url

            announcements.append(
                {
                    'title': titles[i].text_content().strip(),
                    'link': link.strip(),
                }
            )

    result = {
        "status_code": status_code,
        "announcements": announcements,
    }

    return result


def is_file_exist(file_path):
    if path.isfile(file_path):
        return True
    return False


def is_directory_exist(dir_path):
    if path.exists(dir_path):
        return True
    return False


def write_json_file(arr, file_path):
    dir_path = os.path.dirname(os.path.abspath(file_path))

    if is_directory_exist(dir_path):
        current_time = datetime.now()

        json_object = {
            "date_of_update": current_time.strftime("%d-%m-%Y %H:%M:%S"),
            "announcements": arr,
        }

        with open(file_path, 'w+', encoding='utf8') as json_file:
            json.dump(json_object, json_file, ensure_ascii=False)
            json_file.close()
    else:
        os.mkdir(dir_path)


def read_json_file(file_path):
    announcements = []

    if is_file_exist(file_path):
        with open(file_path, 'r', encoding='utf8') as file:
            if file.mode == 'r':
                content = file.read()
                parsed_json = json.loads(content)
                announcements = parsed_json["announcements"]

    return announcements


def send_notification(title, message):
    if title == "" or message == "":
        return

    if len(message) > 300:
        message = message[:300] + "..."

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'key=' + config.server_token,
    }

    body = {
        'notification':
        {
            'title': title,
            'body': message
        },
        'to':
        config.device_token,
            'priority': 'high',
            # 'data': dataPayLoad,
    }

    response = requests.post(
        "https://fcm.googleapis.com/fcm/send", headers=headers, data=json.dumps(body))

    print("Notification was sent. Status", response.status_code)


def compare(new_list, last_list):
    last_titles = list(map(lambda x: x['title'], last_list))
    last_links = list(map(lambda x: x['link'], last_list))

    notification_arr = []
    for item in new_list:
        if not (item["title"] in last_titles and
                item["link"] in last_links):

            notification_arr.append({
                "title": item["title"],
                "link": item["link"],
            })
        else:
            break

    notification_arr.reverse()
    return notification_arr


def log_announcements(department_name, announcements):
    print("-----------------------")
    print(department_name)
    print("-----------------------")

    titles = list(map(lambda x: x['title'], announcements))

    if len(titles) > 0:
        for title in titles:
            print(title)


def run_script():
    for department in config.departments:
        try:
            result = parse_html(
                department["url"],
                department["startingLink"],
                department["titleSelector"],
                department["linkSelector"]
            )

            status_code = result["status_code"]

            if status_code == 200:
                main_path = os.path.dirname(os.path.abspath(__file__))
                file_path = main_path + "\\files\\" + department["fileName"]

                new_announcements = result["announcements"]
                last_announcements = read_json_file(file_path)

                log_announcements(department["name"], new_announcements)

                if is_file_exist(file_path):
                    notifications = compare(
                        new_announcements,
                        last_announcements
                    )

                    for notification in notifications:
                        send_notification(
                            department["name"],
                            notification["title"]
                        )

                write_json_file(new_announcements, file_path)
        except Exception as error:
            print("STATUS CODE: ", status_code)
            print("Error while running run_script() func. : ", error)

            send_notification("Error while running script", str(error))




if __name__ == "__main__":
    print("Script started.")

    WAIT_TIME_SECONDS = 600
    ticker = threading.Event()

    while not ticker.wait(WAIT_TIME_SECONDS):
        run_script()
    
        current_time = datetime.now()
        print(
            "Script has been completed for the last time at: ",
            current_time.strftime("%d-%m-%Y %H:%M:%S")
        )
