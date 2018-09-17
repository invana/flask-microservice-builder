from git import Repo
import json
import os
import shutil
from distutils.dir_util import copy_tree
import logging

logging.basicConfig(level="INFO")
# logging.setLoggerClass(__name__)


WELCOME_MESSAGE = """
#######################################################
#######################################################
############  Invana Microservices Builder ############
=======================================================
=======================================================

"""

APP_TEMPLATE = """

from flask import Flask
from sample_package.api_views import api_blueprint as sample_api_blueprint

if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(sample_api_blueprint)
    app.run()

"""


class MicroServiceBuilder(object):

    def __init__(self, packages_file="microservices.json"):
        self.show_welcome_message()
        self.packages_file = packages_file
        self.packages_data = self.get_packages_data()
        self.CLONE_FOLDER = "cloned_packages-{}".format(self.packages_data['package_version'])
        self.BUILD_FOLDER = "build-{}".format(self.packages_data['package_version'])

    def get_packages_data(self):
        return json.load(open(self.packages_file))

    def show_welcome_message(self):
        logging.info(WELCOME_MESSAGE)

    def clean_folder(self, dir=None):
        try:
            shutil.rmtree(dir)
        except Exception as e:
            pass

    def clean_build(self):
        self.clean_folder(self.BUILD_FOLDER)
        self.clean_folder(self.CLONE_FOLDER)

    def write_line(self, fp=None, line=None):
        fp.write("{}\n".format(line))

    def clone_microservices(self):
        packages_to_clone = self.packages_data['microservices']
        packages_to_clone.update(self.packages_data.get('dependencies', {}))

        for git_url, commit_id in packages_to_clone.items():
            logging.info("Cloning the git_url: {}".format(git_url))
            repo_name = git_url.split("/")[1]
            Repo.clone_from(git_url, "{}/{}".format(self.CLONE_FOLDER, repo_name))

    def create_build(self):
        packages_list = []
        requirements_files_list = []
        packages_to_clone = self.packages_data['microservices']
        packages_to_clone.update(self.packages_data.get('dependencies', {}))
        for git_url, commit_id in packages_to_clone.items():
            repo_name = git_url.split("/")[1]
            package_cloned_folder = "{}/{}".format(self.CLONE_FOLDER, repo_name)
            setup_file = "{}/setup.py".format(package_cloned_folder)
            requirements_file = "{}/requirements.txt".format(package_cloned_folder)
            package_name = open(setup_file).read().split("name=")[1].split(",")[0].strip("'").strip('"')
            package_path = "{}/{}".format(package_cloned_folder, package_name)
            copy_tree(package_path, "{}/{}".format(self.BUILD_FOLDER, package_name))
            packages_list.append(package_name)
            requirements_files_list.append(requirements_file)

        return packages_list, requirements_files_list

    def write_app(self, packages_list):
        app_fp = open("{}/app.py".format(self.BUILD_FOLDER), "w")
        self.write_line(app_fp, "from flask import Flask")
        for package_name in packages_list:
            self.write_line(app_fp,
                            "from {}.api_views import api_blueprint as {}_api_blueprint".format(package_name,
                                                                                                package_name))

        self.write_line(app_fp, "")
        self.write_line(app_fp, "if __name__ == '__main__':")
        self.write_line(app_fp, "\tapp = Flask(__name__)")
        for package_name in packages_list:
            self.write_line(app_fp, "\tapp.register_blueprint({}_api_blueprint)".format(package_name))
        self.write_line(app_fp, "\tapp.run()")

    def create_dockerfile(self, ):
        docker_file_fp = open("{}/Dockerfile".format(self.BUILD_FOLDER), "w")
        self.write_line(docker_file_fp, "FROM python:3.6")

    def create_requirements(self, requirements_files_list):
        all_requirements = []
        for requirements_file in requirements_files_list:
            requirements = open(requirements_file).readlines()
            all_requirements.extend([req.strip("\n") for req in requirements])
        all_requirements = list(set(all_requirements))
        logging.info("all_requirements {}".format(all_requirements))
        requirements_fp = open("{}/requirements.txt".format(self.BUILD_FOLDER), "w")
        for req in all_requirements:
            self.write_line(requirements_fp, req)

    def generate_release_notes(self, ):
        logging.info("Generating the release notes")
        release_notes_fp = open("{}/RELEASE_NOTES".format(self.BUILD_FOLDER), 'w')
        self.write_line(release_notes_fp,
                        "# Release Notes for {}:{}".format(self.packages_data['package_name'],
                                                           self.packages_data['package_version']))
        for git_url, commit_id in self.packages_data['microservices'].items():
            repo_name = git_url.split("/")[1]
            package_cloned_folder = "{}/{}".format(self.CLONE_FOLDER, repo_name)
            setup_file = "{}/setup.py".format(package_cloned_folder)
            package_name = open(setup_file).read().split("name=")[1].split(",")[0].strip("'").strip('"')
            repo = Repo(package_cloned_folder)
            commit_id = repo.commit()
            self.write_line(release_notes_fp, "{} [{}:{}]".format(package_name, git_url, commit_id))

    def generate_build(self):
        self.clean_build()
        self.clone_microservices()
        packages_list, requirements_files_list = self.create_build()
        self.write_app(packages_list)
        self.create_requirements(requirements_files_list)
        self.generate_release_notes()
        self.create_dockerfile()
        self.test_build(packages_list)

    def test_api_views(self, packages_list):
        """
        Check api_views exist

        :param packages_list:
        :return:
        """
        logging.info("Testing the api_views.py")
        error_packages = []
        for package_name in packages_list:
            api_view_exist = os.path.exists("{}/{}/api_views.py".format(self.BUILD_FOLDER, package_name))
            if api_view_exist is False:
                error_packages.append(package_name)
        if len(error_packages) > 0:
            logging.error("api_views.py doesn't exist in the packages : {}".format(error_packages))
        else:
            logging.info("All good with api_views.py; exist in all packages")

        # TODO - Check if api_views has api_blueprint that we can import into main application
        # TODO -Check if add_resource is used to add any route to the blue print

    def test_requirements(self):
        """
        check if any requirements has two  versions specified.
        :return:
        """
        requirements = [req.strip("\n") for req in open("{}/requirements.txt".format(self.BUILD_FOLDER)).readlines()]
        # TODO - check if requirements as any duplicates, because of versions.

    def test_build(self, packages_list, ):
        self.test_api_views(packages_list)
        self.test_requirements()
