import logging
import os
from datetime import datetime

import aiofiles
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi import UploadFile
from sqlalchemy.orm import Session

import config
from core import const, util, cg_container
from core.ATG import ATG
from core.login import models
from core.login import schemas
from core.login.auth_bearer import JWTBearer
from core.login.database import Base, engine, SessionLocal
from core.login.models import User, TokenTable
from core.login.utils import create_access_token, create_refresh_token, verify_password, get_hashed_password, \
    get_user_id_from_token
from core.method_finder import MethodFinder

config.start()

logger = logging.getLogger("Main")

# uvicorn main:app --host 0.0.0.0 --port 1992 --reload
app = FastAPI()

Base.metadata.create_all(engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/")
async def root():
    return {"message": "Hello World!!!!!"}


@app.post("/register")
def register_user(user: schemas.UserCreate, session: Session = Depends(get_session)):
    logger.info(f"begin register: {user.email}")
    existing_user = session.query(models.User).filter_by(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    encrypted_password = get_hashed_password(user.password)
    new_user = models.User(username=user.username, email=user.email, password=encrypted_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"message": "user created successfully"}


@app.post('/login', response_model=schemas.TokenSchema)
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

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    token_db = models.TokenTable(user_id=user.id, access_toke=access, refresh_toke=refresh, status=True)
    db.add(token_db)
    db.commit()
    db.refresh(token_db)
    return {
        "access_token": access,
        "refresh_token": refresh,
    }


@app.get('/getusers')
def getusers(token=Depends(JWTBearer()), session: Session = Depends(get_session)):
    user = session.query(models.User).all()
    return user


# curl -v -X GET -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MjEyMjcyMjEsInN1YiI6IjEifQ.Mp9xwxWlb_1kOGZL5odlyGF28aZV4F1tMXT_GlqodBU" http://localhost:1992/getusers


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


@app.post("/check_uploaded")
async def check_uploaded(package_name: str, version_code: int, token=Depends(JWTBearer())):
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
async def create_upload_file(file: UploadFile, token=Depends(JWTBearer())):
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
async def get_permission(package_name: str, version_code: int, token=Depends(JWTBearer()),
                         db: Session = Depends(get_session)):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(package_name, version_code, cg)
    used_permissions = mf.get_used_permissions()
    user_id = get_user_id_from_token(token)
    last_permissions = db.query(models.HisPermissionTable).filter(
        models.HisPermissionTable.user_id == user_id, models.HisPermissionTable.package_name == package_name).order_by(
        models.HisPermissionTable.created_date.desc()).first()
    if last_permissions:
        last_permissions = last_permissions.permissions.split(",")
        last_permissions = list(set(used_permissions) & set(last_permissions))
    else:
        last_permissions = []
    return {"permissions": used_permissions, "last_debloated_permissions": last_permissions}


# curl -X POST http://101.32.239.114:1992/get_permission?package_name=org.woheller69.spritpreise&version_code=24
# curl -X POST http://101.32.239.114:1992/get_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010

@app.post("/debloat_permission")
async def debloat_permission(package_name: str, version_code: int, permissions: str, token=Depends(JWTBearer()),
                             db: Session = Depends(get_session)):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat permission {permissions} for {apk_name}")
    permission_db = models.HisPermissionTable(user_id=get_user_id_from_token(token), package_name=package_name,
                                              app_version=str(version_code), permissions=permissions)
    db.add(permission_db)
    db.commit()
    db.refresh(permission_db)
    permissions = permissions.split(",")
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(package_name, version_code, cg)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_permission(permissions)
    # to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    # all_methods = [method for method in mf.cg.methods if package_name in method]
    # logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=org.woheller69.spritpreise&version_code=24&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION
# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010&permissions=android.permission.RECEIVE_BOOT_COMPLETED,com.android.vending.BILLING,android.permission.FOREGROUND_SERVICE
# curl -X POST http://101.32.239.114:1992/debloat_permission?package_name=com.zhiliaoapp.musically&version_code=2022903010&permissions=android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_BACKGROUND_LOCATION

def get_activities_with_screenshots(app: str):
    _, activities = util.parse_manifest(app)
    screenshot_dir = f"results/screenshots/{app}"
    screenshot_files = [file.replace('.png', '') for file in os.listdir(screenshot_dir)]
    intersection = set(set(activities) & set(screenshot_files))
    return intersection


@app.post("/get_acitivities")
async def get_activities(package_name: str, version_code: int, token=Depends(JWTBearer()),
                         db: Session = Depends(get_session)):
    apk_name = f"{package_name}-{version_code}"
    screenshots = get_activities_with_screenshots(apk_name)
    screenshots_now = []
    if 'org.wikipedia.diff.ArticleEditDetailsActivity' in screenshots:
        screenshots_now.append('org.wikipedia.diff.ArticleEditDetailsActivity')
        screenshots.remove('org.wikipedia.diff.ArticleEditDetailsActivity')
    if 'org.wikipedia.talk.template.TalkTemplatesActivity' in screenshots:
        screenshots_now.append('org.wikipedia.talk.template.TalkTemplatesActivity')
        screenshots.remove('org.wikipedia.talk.template.TalkTemplatesActivity')
    screenshots_now.extend(screenshots)
    user_id = get_user_id_from_token(token)
    last_selected_activities_db_result = db.query(models.HisActivityTable).filter(
        models.HisActivityTable.user_id == user_id, models.HisActivityTable.package_name == package_name).order_by(
        models.HisActivityTable.created_date.desc()).first()
    if last_selected_activities_db_result:
        last_version = last_selected_activities_db_result.app_version
        screenshots_last = get_activities_with_screenshots(f"{package_name}-{last_version}")
        last_selected_activities = last_selected_activities_db_result.activites.split(",")
        last_selected_activities = list(set(screenshots_now) & set(last_selected_activities))
        new_added_activities = list(set(screenshots_now) - set(screenshots_last))
        if len(new_added_activities) == 0:
            return {"activities": screenshots_now, "last_debloated_activities": last_selected_activities}
        new_atg = ATG()
        new_atg_result = new_atg.add_app_transitions(package_name, str(version_code))
        old_atg = ATG()
        old_atg_result = old_atg.add_app_transitions(package_name, str(last_version))
        diff_atg = new_atg_result - old_atg_result
        if len(diff_atg) == 0:
            return {"activities": screenshots_now, "last_debloated_activities": last_selected_activities}
        new_old_pair = {}
        for transition in diff_atg:
            left, right = transition.split(" -> ")
            if right not in new_old_pair:
                new_old_pair[right] = set()
            new_old_pair[right].add(left)
        for right in new_old_pair.keys():
            if right in new_added_activities:
                lefts = set(new_old_pair[right])
                additional = set(set(lefts) - set(last_selected_activities))
                if len(additional) == 0:
                    last_selected_activities.append(right)
        return {"activities": screenshots_now, "last_debloated_activities": last_selected_activities}
    else:
        last_selected_activities = []
        return {"activities": screenshots_now, "last_debloated_activities": last_selected_activities}


# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=org.woheller69.spritpreise&version_code=24
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=org.wikipedia.alpha&version_code=50476
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=com.amaze.filemanager&version_code=117
# curl -X POST http://101.32.239.114:1992/get_acitivities?package_name=com.zhiliaoapp.musically&version_code=2022903010

@app.post("/debloat_activity")
async def debloat_activity(package_name: str, version_code: int, activity_names: str,
                           token=Depends(JWTBearer()), db: Session = Depends(get_session)):
    apk_name = f"{package_name}-{version_code}"
    logger.info(f"Debloat activity {activity_names} for {apk_name}")
    activity_db = models.HisActivityTable(user_id=get_user_id_from_token(token), package_name=package_name,
                                          app_version=str(version_code), activites=activity_names)
    db.add(activity_db)
    db.commit()
    db.refresh(activity_db)
    activity_names = activity_names.split(",")
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(package_name, version_code, cg)
    to_remove_methods, to_remove_permissions = mf.set_to_remove_activity(activity_names)
    logger.debug(f"removed methods: {to_remove_methods}, removed permissions: {to_remove_permissions}")
    return {"to_remove_methods": to_remove_methods, "to_remove_permissions": to_remove_permissions}


# curl -X POST http://101.32.239.114:1992/debloat_activity?package_name=org.woheller69.spritpreise&version_code=24&activity_names=org.woheller69.spritpreise.activities.ManageLocationsActivity,org.woheller69.spritpreise.activities.AboutActivity
# curl -X POST http://101.32.239.114:1992/debloat_activity?package_name=com.zhiliaoapp.musically&version_code=2022903010&activity_names=com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity,com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity

def save_executed_methods(package_name: str, version_code: int, executed_methods: str, token, db):
    if len(executed_methods) == 0:
        #     retrieve the newest executed methods from the database
        executed_db = db.query(models.HisExecutedTable).filter(
            models.HisExecutedTable.user_id == get_user_id_from_token(token),
            models.HisExecutedTable.package_name == package_name).order_by(
            models.HisExecutedTable.created_date.desc()).first()
        if executed_db:
            executed_methods = executed_db.excuted_methods
    else:
        executed_db = models.HisExecutedTable(user_id=get_user_id_from_token(token), package_name=package_name,
                                              app_version=str(version_code), excuted_methods=executed_methods)
        db.add(executed_db)
        db.commit()
        db.refresh(executed_db)
    return executed_methods

def keep_executed_activities(package_name: str, version_code: int, executed_methods: str, token=Depends(JWTBearer()),
                   db: Session = Depends(get_session)):
    executed_methods = save_executed_methods(package_name, version_code, executed_methods, token, db)
    logger.info(f"Keep only for {package_name} with {executed_methods}")
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(package_name, version_code, cg)
    executed_methods = util.extract_methods_from_requests(executed_methods)
    to_remove_methods = mf.keep_activity_only(executed_methods)
    # to_remove_methods = mf.keep_only(executed_methods)
    to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    all_methods = [method for method in mf.cg.methods if package_name in method]
    logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    return to_remove_methods


@app.post("/keeponly")
async def keeponly(package_name: str, version_code: int, executed_methods: str, token=Depends(JWTBearer()),
                   db: Session = Depends(get_session)):
    # executed_methods = save_executed_methods(package_name, version_code, executed_methods, token, db)
    # logger.info(f"Keep only for {package_name} with {executed_methods}")
    # apk_name = f"{package_name}-{version_code}"
    # cg = cg_container.get_cg(apk_name)
    # mf = MethodFinder(package_name, version_code, cg)
    # executed_methods = util.extract_methods_from_requests(executed_methods)
    # to_remove_methods = mf.keep_activity_only(executed_methods)
    # # to_remove_methods = mf.keep_only(executed_methods)
    # to_remove_methods = util.keep_package_only(to_remove_methods, [package_name])
    # all_methods = [method for method in mf.cg.methods if package_name in method]
    # logger.info(f"removed methods size: {len(to_remove_methods)} in all methods {len(all_methods)}")
    to_remove_methods = keep_executed_activities(package_name, version_code, executed_methods, token, db)
    return {"to_remove_methods": to_remove_methods}


# curl -X POST http://101.32.239.114:1992/keeponly?package_name=org.woheller69.spritpreise&version_code=24&&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://101.32.239.114:1992/keeponly?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ%28android.content.Intent%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E

def generalization(package_name: str, version_code: int, executed_methods: str, threshold: float):
    apk_name = f"{package_name}-{version_code}"
    cg = cg_container.get_cg(apk_name)
    mf = MethodFinder(package_name, version_code, cg)
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
async def similar(package_name: str, version_code: int, executed_methods: str, token=Depends(JWTBearer()),
                  db: Session = Depends(get_session)):
    # executed_methods = save_executed_methods(package_name, version_code, executed_methods, token, db)
    # result = generalization(package_name, version_code, executed_methods, 0.7)
    result = keep_executed_activities(package_name, version_code, executed_methods, token, db)
    return {"to_remove_methods": result}


# curl -X POST http://101.32.239.114:1992/similar?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://localhost:1992/similar?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28X.GcL%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ%28X.GcK%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ%28com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ%28boolean%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState%28android.os.Bundle%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ%28android.content.Intent%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume%28%29%3E%2C%3C%20com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E

@app.post("/more")
async def more(package_name: str, version_code: int, executed_methods: str, token=Depends(JWTBearer()),
               db: Session = Depends(get_session)):
    # executed_methods = save_executed_methods(package_name, version_code, executed_methods, token, db)
    # result = generalization(package_name, version_code, executed_methods, 0.9)
    result = keep_executed_activities(package_name, version_code, executed_methods, token, db)
    return {"to_remove_methods": result}


# curl -X POST http://101.32.239.114:1992/more?package_name=org.woheller69.spritpreise&version_code=24&executed_methods=%3Corg.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20org.woheller69.spritpreise.database.CityToWatch%20convertCityToWatched%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20int%20getNavigationDrawerID%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onResume%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20onDestroy%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20addCityToList%28org.woheller69.spritpreise.database.City%29%3E%2C%3C%20org.woheller69.spritpreise.activities.AboutActivity%3A%20void%20onCreate%28android.os.Bundle%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20void%20%3Cinit%3E%28%29%3E%2C%3C%20org.woheller69.spritpreise.activities.ManageLocationsActivity%3A%20int%20getNavigationDrawerID%28%29%3E
# curl -X POST http://localhost:1992/more?package_name=com.zhiliaoapp.musically&version_code=2022903010&executed_methods=%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20X.X6W%20getInflater()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onCreate(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onSaveInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(X.GcL)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZJ(X.GcK)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZ(com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20dJ_()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LIZIZ(boolean)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20onRestoreInstanceState(android.os.Bundle)%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20finish()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20void%20LJII()%3E-%2C-%3Ccom.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity%3A%20boolean%20LIZ(android.content.Intent)%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20java.lang.String%20getBtmPageCode()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onPause()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStop()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20%3Cinit%3E()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20android.content.Intent%20getIntent()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onDestroy()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onStart()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onResume()%3E-%2C-%3Ccom.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity%3A%20void%20onCreate(android.os.Bundle)%3E

@app.post('/logout')
def logout(token=Depends(JWTBearer()), db: Session = Depends(get_session)):
    user_id = get_user_id_from_token(token)
    token_record = db.query(models.TokenTable).all()
    info = []
    for record in token_record:
        print("record", record)
        if (datetime.utcnow() - record.created_date).days > 1:
            info.append(record.user_id)
    if info:
        existing_token = db.query(models.TokenTable).where(TokenTable.user_id.in_(info)).delete()
        db.commit()
    existing_token = db.query(models.TokenTable).filter(models.TokenTable.user_id == user_id,
                                                        models.TokenTable.access_toke == token).first()
    if existing_token:
        existing_token.status = False
        db.add(existing_token)
        db.commit()
        db.refresh(existing_token)
    return {"message": "Logout Successfully"}


# curl -v -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MjEyMjcyMjEsInN1YiI6IjEifQ.Mp9xwxWlb_1kOGZL5odlyGF28aZV4F1tMXT_GlqodBU" http://localhost:1992/logout

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1992)
# The login related code is referenced from: https://medium.com/@chnarsimha986/fastapi-login-logout-changepassword-4c12e92d41e2
