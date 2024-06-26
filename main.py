import logging
import time
import uvicorn

import os

if not os.path.exists("log"):
    os.makedirs("log")

# time in yyyy-mm-dd-hh-mm-ss
current_time = time.strftime("%Y-%m-%d-%H-%M-%S")
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=f"log/{current_time}.log",
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

import json

import os

import aiofiles
from fastapi import FastAPI, UploadFile

from core import const, util, cg_container
from core.method_finder import MethodFinder

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
    permissions, _ = util.parse_manifest(apk_name)
    return {"permissions": permissions}


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
    mf = MethodFinder(apk_name, cg, neeed_slicing=True)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_permission(permissions)
    to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    all_methods = [method for method in mf.cg.methods if package_name in method]
    logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
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

if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=1992)