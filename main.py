import json
import os
import subprocess

import aiofiles
from fastapi import FastAPI, UploadFile

from urllib.parse import unquote

import logging

import pandas as pd
from core import const, util, cg_container
from core.method_finder import MethodFinder
import log_config

# uvicorn main:app --host 0.0.0.0 --port 1992 --reload
app = FastAPI()

logger = logging.getLogger("main")
similarity_mapping = {}


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
# curl -X POST http://localhost:1992/get_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010

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
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    mapping = mf.get_permission_acitivity_mapping()
    return {"acitivy_permissions": mapping}


# curl -X POST http://localhost:1992/get_permission_acitivity_mapping?package_name=org.woheller69.spritpreise&version_code=24
# do not try this (get_permission_acitivity_mapping) with tiktok

@app.post("/debloat_activity")
async def debloat_activity(package_name: str, version_code: int, activity_names: str):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat activity {activity_names} for {apk_name}")
    activity_names = activity_names.split(",")
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_activity(activity_names)
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://localhost:8000/debloat_activity?package_name=cf.playhi.freezeyou&version_code=149&activity_names=cf.playhi.freezeyou.ui.InstallPackagesActivity,cf.playhi.freezeyou.ui.ManualModeActivity
# curl -X POST http://localhost:1992/debloat_activity?package_name=org.woheller69.spritpreise&version_code=24&activity_names=org.woheller69.spritpreise.activities.ManageLocationsActivity,org.woheller69.spritpreise.activities.AboutActivity
# curl -X POST http://localhost:1992/debloat_activity?package_name=com.zhiliaoapp.musically&version_code=2022903010&activity_names=com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity,com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity


@app.post("/debloat_permission")
async def debloat_permission(package_name: str, version_code: int, permissions: str):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat permission {permissions} for {apk_name}")
    permissions = permissions.split(",")
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_permission(permissions)
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://localhost:8000/debloat_permission?package_name=cf.playhi.freezeyou&version_code=149&permissions=android.permission.USE_BIOMETRIC,android.permission.WRITE_EXTERNAL_STORAGE
# curl -X POST http://localhost:8000/debloat_permission?package_name=org.woheller69.spritpreise&version_code=24&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION
# curl -X POST http://localhost:1992/debloat_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010&permissions=android.permission.RECEIVE_BOOT_COMPLETED,com.android.vending.BILLING,android.permission.FOREGROUND_SERVICE

def initialize_similarity():
    for apk_name in os.listdir("apks"):
        apk_name = apk_name.replace(".apk", "")
        logger.info(f"calculating the cosine similarity {apk_name}")
        similarities = util.calculate_similarity(apk_name)
        if similarities is None:
            logger.info(f"Similarity for {apk_name} is not ready.")
            continue
        logger.info(f"Similarity for {apk_name} is ready.")
        similarity_mapping[apk_name] = similarities

initialize_similarity()

def get_similarity_df(apk_name: str):
    if apk_name not in similarity_mapping:
        return None
    return similarity_mapping[apk_name]

@app.get("/record")
async def get_similarity(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    embedding_path = const.get_embedding_file(apk_name)
    # if not os.path.exists(embedding_path) or not os.path.exists(similarity_path):
    if not os.path.exists(embedding_path):
        cg_file = const.get_cg_file(apk_name)
        if not os.path.exists(cg_file):
            logger.info(f"cg file not exists for {apk_name}")
            return None
        logger.info(f"calculating the embedding {apk_name}")
        subprocess.Popen(["pecanpy", "--input", const.get_cg_file(apk_name), "--output", embedding_path, "--mode", "FirstOrderUnweighted", "--delimiter", " -> "])
    else:
        get_similarity_df(apk_name)
    return {"message": "Processing"}


#  curl http://localhost:1992/record?package_name=org.woheller69.spritpreise&version_code=24
#  curl http://localhost:1992/record?package_name=com.amaze.filemanager&version_code=117
#  curl http://localhost:1992/record?package_name=org.wikipedia&version_code=268
#  curl http://localhost:1992/record?package_name=com.zhiliaoapp.musically&version_code=2022903010
#  curl http://localhost:1992/record?package_name=org.woheller69.spritpreise&version_code=18

@app.post("/keeponly")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    to_remove_methods = mf.keep_only(executed_methods.split("-,-"))
    return {"to_remove_methods": to_remove_methods}

# curl -X POST http://localhost:1992/keeponly?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID()%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID()%3E
# curl -X POST http://localhost:1992/keeponly?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ(android.content.Intent)%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate(android.os.Bundle)%3E


@app.post("/similar")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    result_dict = {}
    threshold = 0.7
    similarity_df = get_similarity_df(apk_name)
    if similarity_df is None:
        return {"to_remove_methods": "Similarity not ready"}
    to_remove_methods = mf.generalization(threshold, executed_methods.split("-,-"), similarity_df)
    result_dict[threshold] = to_remove_methods
    result = json.dumps(result_dict)
    return {"to_remove_methods": result}
# curl -X POST http://localhost:1992/similar?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID()%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID()%3E
# curl -X POST http://localhost:1992/similar?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ(android.content.Intent)%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate(android.os.Bundle)%3E

@app.post("/more")
async def generalization(package_name: str, version_code: int, executed_methods: str):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    executed_methods = unquote(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods}")
    result_dict = {}
    threshold = 0.9
    similarity_df = get_similarity_df(apk_name)
    if similarity_df is None:
        return {"to_remove_methods": "Similarity not ready"}
    to_remove_methods = mf.generalization(threshold, executed_methods.split("-,-"), similarity_df)
    result_dict[threshold] = to_remove_methods
    result = json.dumps(result_dict)
    return {"to_remove_methods": result}
# curl -X POST http://localhost:1992/more?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID()%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList(org.woheller69.spritpreise.database.City)%3E-%2C-%3Corg.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID()%3E
