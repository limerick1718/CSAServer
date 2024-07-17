import os
import logging
import uvicorn

import log_config

from typing import Annotated

import aiofiles
from fastapi import FastAPI, UploadFile, Depends
from fastapi.security import OAuth2PasswordBearer

from core import const, util, cg_container
from core.method_finder import MethodFinder

from core.login import schemas
from core.login import models
import jwt
from datetime import datetime 
from core.login.models import User,TokenTable
from core.login. database import Base, engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from core.login.auth_bearer import JWTBearer
from functools import wraps
from core.login.utils import create_access_token,create_refresh_token,verify_password,get_hashed_password

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = "narscbjim@$@&^@&%^&RFghgjvbdsha"   # should be kept secret
JWT_REFRESH_SECRET_KEY = "13ugfdfgh@#$%^@&jkl45678902"

log_config.start()

logger = logging.getLogger("Main")

# uvicorn main:app --host 0.0.0.0 --port 1992 --reload
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World!!!!!"}


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


# curl -F 'file=@/Users/jiakun/Downloads/org.woheller69.spritpreise_24.apk' http://101.32.239.114:1992/uploadfile
# curl -F 'file=@/Users/jiakun/Downloads/apks/wikipedia.apk' http://localhost:1992/uploadfile

@app.post("/get_permission")
async def get_permission(package_name: str, version_code: int):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    used_permissions = mf.get_used_permissions()
    return {"permissions": used_permissions}


# curl -X POST http://101.32.239.114:1992/get_permission?package_name=org.woheller69.spritpreise&version_code=24
# curl -X POST http://101.32.239.114:1992/get_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010

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


# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=org.woheller69.spritpreise&version_code=24
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=org.wikipedia.alpha&version_code=50476
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=com.amaze.filemanager&version_code=117
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=com.zhiliaoapp.musically&version_code=2022903010

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


# curl -X POST http://101.32.239.114:1992/debloat_activity?package_name=org.woheller69.spritpreise&version_code=24&activity_names=org.woheller69.spritpreise.activities.ManageLocationsActivity,org.woheller69.spritpreise.activities.AboutActivity
# curl -X POST http://101.32.239.114:1992/debloat_activity?package_name=com.zhiliaoapp.musically&version_code=2022903010&activity_names=com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity,com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity

@app.post("/debloat_permission")
async def debloat_permission(package_name: str, version_code: int, permissions: str):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat permission {permissions} for {apk_name}")
    permissions = permissions.split(",")
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_permission(permissions)
    # to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    # all_methods = [method for method in mf.cg.methods if package_name in method]
    # logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=org.woheller69.spritpreise&version_code=24&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION
# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010&permissions=android.permission.RECEIVE_BOOT_COMPLETED,com.android.vending.BILLING,android.permission.FOREGROUND_SERVICE
# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION


@app.post("/keeponly")
async def keeponly(package_name: str, version_code: int, executed_methods: str):
    logger.info(f"Keep only for {package_name} with {executed_methods}")
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    executed_methods = util.extract_methods_from_requests(executed_methods)
    to_remove_methods = mf.keep_only(executed_methods)
    to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    all_methods = [method for method in mf.cg.methods if package_name in method]
    logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    return {"to_remove_methods": to_remove_methods}


# curl -X POST http://101.32.239.114:1992/keeponly?package_name=org.woheller69.spritpreise&version_code=24&&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://101.32.239.114:1992/keeponly?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ%28android.content.Intent%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E

def generalization(package_name: str, version_code: int, executed_methods: str, threshold: float):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(apk_name, cg)
    similarity_matrix, indices = util.load_similarity_file(apk_name, threshold)
    logger.info(f"Load similarity file for {apk_name} finish")
    if similarity_matrix is None:
        return {"to_remove_methods": "Similarity not ready"}
    executed_methods = util.extract_methods_from_requests(executed_methods)
    logger.info(f"Generalization for {apk_name} with {executed_methods} using threshold {threshold}")
    to_remove_methods = mf.generalization(executed_methods, similarity_matrix, indices)
    to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    all_methods = [method for method in mf.cg.methods if package_name in method]
    logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    # result_dict = {}
    # result_dict[threshold] = to_remove_methods
    # result = json.dumps(result_dict)
    return to_remove_methods

@app.post("/similar")
async def similar(package_name: str, version_code: int, executed_methods: str):
    result = generalization(package_name, version_code, executed_methods, 0.7)
    return {"to_remove_methods": result}


# curl -X POST http://101.32.239.114:1992/similar?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://localhost:1992/similar?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ%28android.content.Intent%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E

@app.post("/more")
async def more(package_name: str, version_code: int, executed_methods: str):
    result = generalization(package_name, version_code, executed_methods, 0.9)
    return {"to_remove_methods": result}
# curl -X POST http://101.32.239.114:1992/more?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://localhost:1992/more?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ(android.content.Intent)%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate(android.os.Bundle)%3E

Base.metadata.create_all(engine)
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@app.post("/register")
def register_user(user: schemas.UserCreate, session: Session = Depends(get_session)):
    logger.info(f"begin register: {user.email}")
    existing_user = session.query(models.User).filter_by(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    encrypted_password =get_hashed_password(user.password)
    new_user = models.User(username=user.username, email=user.email, password=encrypted_password )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message":"user created successfully"}

@app.post('/login' ,response_model=schemas.TokenSchema)
def login(request: schemas.requestdetails, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.email == request.email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email")
    hashed_pass = user.password
    if not verify_password(request.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    access=create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    token_db = models.TokenTable(user_id=user.id,  access_toke=access,  refresh_toke=refresh, status=True)
    db.add(token_db)
    db.commit()
    db.refresh(token_db)
    return {
        "access_token": access,
        "refresh_token": refresh,
    }

@app.get('/getusers')
def getusers(session: Session = Depends(get_session)):
    user = session.query(models.User).all()
    return user

@app.post('/change-password')
def change_password(request: schemas.changepassword, db: Session = Depends(get_session)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
    
    if not verify_password(request.old_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid old password")
    
    encrypted_password = get_hashed_password(request.new_password)
    user.password = encrypted_password
    db.commit()
    
    return {"message": "Password changed successfully"}

@app.post('/logout')
def logout(dependencies=Depends(JWTBearer()), db: Session = Depends(get_session)):
    token=dependencies
    payload = jwt.decode(token, JWT_SECRET_KEY, ALGORITHM)
    user_id = payload['sub']
    token_record = db.query(models.TokenTable).all()
    info=[]
    for record in token_record :
        print("record",record)
        if (datetime.utcnow() - record.created_date).days >1:
            info.append(record.user_id)
    if info:
        existing_token = db.query(models.TokenTable).where(TokenTable.user_id.in_(info)).delete()
        db.commit()
    existing_token = db.query(models.TokenTable).filter(models.TokenTable.user_id == user_id, models.TokenTable.access_toke==token).first()
    if existing_token:
        existing_token.status=False
        db.add(existing_token)
        db.commit()
        db.refresh(existing_token)
    return {"message":"Logout Successfully"}

# curl -v -X POST -H "Authorization: Bearer narscbjim@$@&^@&%^&RFghgjvbdsha" http://101.32.239.114:1992/logout
# curl -v -X POST -H "Authorization: Bearer narscbjim@$@&^@&%^&RFghgjvbdsha" http://localhost:1992/logout

def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        payload = jwt.decode(kwargs['dependencies'], JWT_SECRET_KEY, ALGORITHM)
        user_id = payload['sub']
        data= kwargs['session'].query(models.TokenTable).filter_by(user_id=user_id,access_toke=kwargs['dependencies'],status=True).first()
        if data:
            return func(kwargs['dependencies'],kwargs['session'])
        else:
            return {'msg': "Token blocked"}
    return wrapper

if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=1992)