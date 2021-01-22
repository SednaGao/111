import os


def get_module_list():
    APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
    file_list = os.listdir(APP_PATH)
    app_list = []
    for file_name in file_list:
        file_path = os.path.join(APP_PATH, file_name)
        if os.path.isdir(file_path) and file_name not in ['static', 'templates', '__pycache__']:
            app_list.append(file_name)
    return app_list


if __name__ == '__main__':
    print(get_module_list())
