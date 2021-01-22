from colorama import Fore, init
from flask_sqlalchemy import SQLAlchemy

from flask import current_app
from flask_script import Manager, prompt
from flask_migrate import Migrate, MigrateCommand
from app import create_app, db, FinalUser, user_datastore
from config.config import DevelopmentConfig
from flask_security import utils
from utils.app_methods import get_module_list

import re
import os

from lib.module_generator.generator import MVCGenerator
from lib.flask_doc import Generator

app = create_app('development')

generator = Generator(app, get_module_list())
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def createmodule():
    path = prompt(Fore.BLUE + "Write the name of the blueprint")
    try:
        int(path)
        print(Fore.RED + "Name no valid")
        return
    except ValueError:
        pass
    folder = current_app.config['APP_FOLDER'] + path
    register_blueprint_str = "Blueprint('{0}', 'app.{0}', template_folder='templates', url_prefix='/{0}')".format(
        path.lower())
    if not os.path.exists(folder):
        mvc_generator = MVCGenerator(name=path, folder=folder, is_sql=isinstance(db, SQLAlchemy))
        mvc_generator.generate_mvc()
        # Register blueprint in app/route.py
        route_path = os.path.join(current_app.config['APP_FOLDER'], "routes.py")
        with open(route_path, "r") as old_routes:
            data = old_routes.readlines()
            i = len(data) - 1
            while i >= 0:
                if ']' not in data[i]:
                    i -= 1
                else:
                    break
            data[i] = "    " + register_blueprint_str + ',\n' + data[i]

        with open(route_path, 'w') as new_routes:
            new_routes.writelines(data)
    else:
        print(Fore.RED + "This path exist")


@manager.command
def createadmin():
    email = prompt(Fore.BLUE + "Email")
    query_email = db.session.query(FinalUser).filter_by(email=email).first()
    if query_email is None:
        password = prompt(Fore.BLUE + "Write password")
        repeat_password = prompt(Fore.BLUE + "Repeat password")
        if password == repeat_password:
            encrypted_password = utils.encrypt_password(password)
            user_datastore.create_user(email=email,
                                       password=encrypted_password)
            db.session.commit()
            user_datastore.add_role_to_user(email, 'admin')
            db.session.commit()
            print(Fore.GREEN + "Admin created")
        else:
            print(Fore.RED + "The password does not match")
            return
    else:
        print(Fore.RED + "The username or email are in use")
        return


if __name__ == '__main__':
    generator.prepare()
    manager.run()
