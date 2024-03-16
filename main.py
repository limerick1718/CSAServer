import json
import os
import subprocess

import aiofiles
from fastapi import FastAPI, UploadFile

from urllib.parse import unquote

import logging
from core import const, util
from core.method_finder import MethodFinder
import log_config

# uvicorn main:app --host 0.0.0.0 --port 1992 --reload
app = FastAPI()

logger = logging.getLogger("main")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/check_uploaded")
async def check_uploaded(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    apk_file_path = f"{const.apk_dir}/{apk_name}.apk"
    if os.path.exists(apk_file_path):
        util.get_call_graph(apk_name)
        logger.info(f"{apk_name} already exists.")
        return {"message": "File exists"}
    else:
        logger.info(f"{apk_name} not exists.")
        return {"message": "File not exists"}


# curl -X POST http://localhost:1992/check_uploaded?package_name=cf.playhi.freezeyou&version_code=149

@app.post("/uploadfile")
async def create_upload_file(file: UploadFile):
    temp_out_file_path = f"{const.upload_temp_dir}/{file.filename}"
    async with aiofiles.open(temp_out_file_path, 'wb') as out_file:
        while content := await file.read(1024):  # async read chunk
            await out_file.write(content)  # async write chunk
    new_name = util.get_new_name(temp_out_file_path)
    new_file_path = f"{const.apk_dir}/{new_name}.apk"
    os.rename(temp_out_file_path, new_file_path)
    util.get_call_graph(new_name)
    logger.info(f"File {new_name} uploaded.")
    return {"filename": file.filename}


# curl -F 'file=@/Users/jiakun/Projects/CSAServer/apks/org.woheller69.spritpreise-24.apk' http://localhost:8000/uploadfile
# curl -F 'file=@/Users/jiakun/Downloads/apks/wikipedia.apk' http://localhost:1992/uploadfile

# @app.post("/get_acitivity")
# async def get_acitivity(package_name: str, version_code: int):
#     apk_name = f"{package_name}-{version_code}"
#     _, activities = util.parse_manifest(apk_name)
#     return {"activities": activities}


# curl -X POST http://localhost:1992/get_acitivity?package_name=org.woheller69.spritpreise&version_code=24

@app.post("/get_permission")
async def get_permission(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    permissions, _ = util.parse_manifest(apk_name)
    return {"permissions": permissions}


# curl -X POST http://localhost:1992/get_permission?package_name=org.woheller69.spritpreise&version_code=24

@app.post("/get_acitivities")
async def get_permission(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    _, activities = util.parse_manifest(apk_name)
    logger.info(f"activities for {activities}")
    screenshot_dir = f"results/screenshots/{apk_name}"
    screenshot_files = [file.replace('.png', '') for file in os.listdir(screenshot_dir)]
    logger.info(f"screenshot_files for {screenshot_files}")
    intersection = list(set(activities) & set(screenshot_files))
    # urls = [f"https://raw.githubusercontent.com/limerick1718/CSAServer/master/results/screenshots/{apk_name}/{activity}.png" for activity in intersection]
    return {"activities": intersection}

# curl -X POST http://localhost:1992/get_acitivities?package_name=org.woheller69.spritpreise&version_code=24
# curl -X POST http://localhost:1992/get_acitivities?package_name=org.wikipedia.alpha&version_code=50476
# curl -X POST http://localhost:1992/get_acitivities?package_name=com.amaze.filemanager&version_code=117
# curl -X POST http://localhost:1992/get_acitivities?package_name=com.zhiliaoapp.musically&version_code=2022903010

@app.post("/get_permission_acitivity_mapping")
async def get_permission_acitivity_mapping(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    mf = MethodFinder(apk_name)
    mapping = mf.get_permission_acitivity_mapping()
    return {"acitivy_permissions": mapping}


# curl -X POST http://localhost:8000/get_permission_acitivity_mapping?package_name=org.woheller69.spritpreise&version_code=24

@app.post("/debloat_activity")
async def debloat_activity(package_name: str, version_code: int, activity_names: str):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat activity {activity_names} for {apk_name}")
    activity_names = activity_names.split(",")
    mf = MethodFinder(apk_name)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_activity(activity_names)
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://localhost:8000/debloat_activity?package_name=cf.playhi.freezeyou&version_code=149&activity_names=cf.playhi.freezeyou.ui.InstallPackagesActivity,cf.playhi.freezeyou.ui.ManualModeActivity
# curl -X POST http://localhost:1992/debloat_activity?package_name=org.woheller69.spritpreise&version_code=24&activity_names=org.woheller69.spritpreise.activities.ManageLocationsActivity,org.woheller69.spritpreise.activities.AboutActivity

@app.post("/debloat_permission")
async def debloat_permission(package_name: str, version_code: int, permissions: str):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat permission {permissions} for {apk_name}")
    permissions = permissions.split(",")
    mf = MethodFinder(apk_name)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_permission(permissions)
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://localhost:8000/debloat_permission?package_name=cf.playhi.freezeyou&version_code=149&permissions=android.permission.USE_BIOMETRIC,android.permission.WRITE_EXTERNAL_STORAGE
# curl -X POST http://localhost:8000/debloat_permission?package_name=org.woheller69.spritpreise&version_code=24&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION

@app.get("/record")
async def get_similarity(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    embedding_path = const.get_embedding_file(apk_name)
    similarity_path = const.get_similarity_file(apk_name)
    if not os.path.exists(embedding_path) or not os.path.exists(similarity_path):
        subprocess.Popen(["python", "similarity_cal.py", apk_name])
    return {"message": "Processing"}


#  curl http://localhost:1992/record?package_name=org.woheller69.spritpreise&version_code=24
#  curl http://localhost:1992/record?package_name=com.amaze.filemanager&version_code=117
#  curl http://localhost:1992/record?package_name=org.wikipedia&version_code=268
#  curl http://localhost:1992/record?package_name=com.zhiliaoapp.musically&version_code=2022903010
#  curl http://localhost:1992/record?package_name=org.woheller69.spritpreise&version_code=18

@app.post("/keeponly")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    mf = MethodFinder(apk_name)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    to_remove_methods = mf.keep_only(executed_methods.split(","))
    return {"to_remove_methods": to_remove_methods}

# curl -X POST http://localhost:1992/keeponly?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E


@app.post("/similar")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    mf = MethodFinder(apk_name)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    result_dict = {}
    threshold = 0.7
    to_remove_methods = mf.generalization(threshold, executed_methods.split(","))
    result_dict[threshold] = to_remove_methods
    result = json.dumps(result_dict)
    return {"to_remove_methods": result}
# curl -X POST http://localhost:1992/similar?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E

@app.post("/more")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    mf = MethodFinder(apk_name)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    result_dict = {}
    threshold = 0.9
    to_remove_methods = mf.generalization(threshold, executed_methods.split(","))
    result_dict[threshold] = to_remove_methods
    result = json.dumps(result_dict)
    return {"to_remove_methods": result}
# curl -X POST http://localhost:1992/more?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
