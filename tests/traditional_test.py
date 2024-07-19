from fastapi.testclient import TestClient
import main
import json

client = TestClient(main.app)

request_dict = {
    "email": "test@qwq.com",
    "password": "asdfa_new"
}
request_json = json.dumps(request_dict)
request = client.build_request(
    method="post",
    url="/login",
    data=request_json
)
response = client.send(request)
result = response.json()
access_token = result['access_token']
refresh_token = result['refresh_token']


def test_avaiblable():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World!!!!!"}


def test_check_upload():
    request = client.build_request(
        method="post",
        url="/check_uploaded",
        params={"package_name": "cf.playhi.freezeyou", "version_code": "149"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    response = client.send(request)
    result = response.json()
    assert result == {'message': 'File not exists'}

    request = client.build_request(
        method="post",
        url="/check_uploaded",
        params={"package_name": "cf.playhi.freezeyou", "version_code": "149"},
    )
    response = client.send(request)
    result = response.json()
    assert result == {'detail': 'Not authenticated'}


def test_get_permission():
    request = client.build_request(method="POST",
                                   url="/get_permission",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    result = response.json()
    assert result['permissions'] == ["android.permission.ACCESS_COARSE_LOCATION"]
    assert result['last_debloated_permissions'] == []

    request = client.build_request(method="POST",
                                   url="/get_permission",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    result = response.json()
    assert set(result['permissions']) == {'android.permission.SYSTEM_ALERT_WINDOW', 'android.permission.RECORD_AUDIO',
                                          'android.permission.CAMERA', 'android.permission.WAKE_LOCK',
                                          'android.permission.WRITE_EXTERNAL_STORAGE',
                                          'android.permission.FOREGROUND_SERVICE', 'android.permission.INTERNET'}
    assert result['last_debloated_permissions'] == []


def test_debloat_permission():
    request = client.build_request(method="POST",
                                   url="/debloat_permission",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24", "permissions": "android.permission.ACCESS_COARSE_LOCATION"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert set(response.json()["to_remove_methods"]) == {
        '<androidx.appcompat.app.TwilightManager: android.location.Location getLastKnownLocationForProvider(java.lang.String)>'}
    assert set(response.json()["to_remove_permissions"]) == {"android.permission.ACCESS_COARSE_LOCATION"}

    request = client.build_request(method="POST",
                                   url="/debloat_permission",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010", "permissions": "android.permission.SYSTEM_ALERT_WINDOW,android.permission.WAKE_LOCK,android.permission.FOREGROUND_SERVICE"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert set(response.json()["to_remove_methods"]) == {
        '<android.app.Service: void startForeground(int,android.app.Notification)>',
        '<android.media.MediaPlayer: void release()>',
        '<android.media.MediaPlayer: void reset()>',
        '<android.media.MediaPlayer: void start()>',
        '<android.media.MediaPlayer: void stop()>',
        '<android.provider.Settings: boolean canDrawOverlays(android.content.Context)>'}
    assert set(response.json()["to_remove_permissions"]) == {"android.permission.WAKE_LOCK",
                                                             "android.permission.SYSTEM_ALERT_WINDOW",
                                                             "android.permission.FOREGROUND_SERVICE"}


def test_get_permission_after_debloated():
    request = client.build_request(method="POST",
                                   url="/get_permission",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    result = response.json()
    assert result['permissions'] == ["android.permission.ACCESS_COARSE_LOCATION"]
    assert result['last_debloated_permissions'] == ["android.permission.ACCESS_COARSE_LOCATION"]

    request = client.build_request(method="POST",
                                   url="/get_permission",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    result = response.json()
    assert set(result['permissions']) == {'android.permission.SYSTEM_ALERT_WINDOW', 'android.permission.RECORD_AUDIO',
                                          'android.permission.CAMERA', 'android.permission.WAKE_LOCK',
                                          'android.permission.WRITE_EXTERNAL_STORAGE',
                                          'android.permission.FOREGROUND_SERVICE', 'android.permission.INTERNET'}
    assert set(result['last_debloated_permissions']) == {"android.permission.WAKE_LOCK",
                                                         "android.permission.SYSTEM_ALERT_WINDOW",
                                                         "android.permission.FOREGROUND_SERVICE"}


def test_get_acitivities():
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"org.woheller69.spritpreise.activities.AboutActivity",
                          "org.woheller69.spritpreise.firststart.TutorialActivity",
                          "org.woheller69.spritpreise.activities.ManageLocationsActivity",
                          "org.woheller69.spritpreise.activities.SettingsActivity",
                          "org.woheller69.spritpreise.activities.CityGasPricesActivity"}
    assert set(response.json()["last_debloated_activities"]) == set()
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "org.wikipedia.alpha", "version_code": "50476"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"org.wikipedia.settings.languages.WikipediaLanguagesActivity",
                          "org.wikipedia.places.PlacesActivity",
                          "org.wikipedia.theme.ThemeFittingRoomActivity",
                          "org.wikipedia.main.MainActivity", "org.wikipedia.page.tabs.TabActivity",
                          "org.wikipedia.edit.EditSectionActivity",
                          "org.wikipedia.page.PageActivity",
                          "org.wikipedia.talk.TalkTopicsActivity",
                          "org.wikipedia.talk.TalkReplyActivity",
                          "org.wikipedia.language.LanguagesListActivity",
                          "org.wikipedia.diff.ArticleEditDetailsActivity",
                          "org.wikipedia.createaccount.CreateAccountActivity",
                          "org.wikipedia.settings.AboutActivity",
                          "org.wikipedia.language.LangLinksActivity",
                          "org.wikipedia.readinglist.ReadingListActivity",
                          "org.wikipedia.page.edithistory.EditHistoryListActivity",
                          "org.wikipedia.feed.configure.ConfigureActivity",
                          "org.wikipedia.settings.SettingsActivity",
                          "org.wikipedia.onboarding.InitialOnboardingActivity",
                          "org.wikipedia.settings.LicenseActivity",
                          "org.wikipedia.search.SearchActivity"}
    assert set(response.json()["last_debloated_activities"]) == set()
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "com.amaze.filemanager", "version_code": "117"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"com.amaze.filemanager.ui.activities.AboutActivity",
                          "com.amaze.filemanager.ui.activities.PreferencesActivity",
                          "com.amaze.filemanager.ui.activities.MainActivity",
                          "com.amaze.filemanager.ui.activities.texteditor.TextEditorActivity",
                          "com.mikepenz.aboutlibraries.ui.LibsActivity"}
    assert set(response.json()["last_debloated_activities"]) == set()
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"com.ss.android.ugc.aweme.livewallpaper.ui.LocalLiveWallPaperActivity",
                          "com.ss.android.ugc.aweme.ecommerce.showcase.showcase.ShowcaseActivity",
                          "com.ss.android.ugc.aweme.share.qrcode.UserQRCodeActivity",
                          "com.ss.android.ugc.aweme.crossplatform.activity.CrossPlatformActivity",
                          "com.ss.android.ugc.aweme.compliance.business.filtervideo.ui.activity.FilterVideoKeywordsActivity",
                          "com.ss.android.ugc.aweme.ecommerce.base.pdp.ui.PdpActivity",
                          "com.ss.android.ugc.aweme.detail.ui.DetailActivity",
                          "com.ss.android.ugc.aweme.qrcode.view.ScanQRCodeActivityV2",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.inference.AdInferenceActivity",
                          "com.ss.android.ugc.aweme.live.LivePlayActivity",
                          "com.ss.android.ugc.aweme.setting.ui.PushSettingNotificationChoiceActivity",
                          "com.ss.android.ugc.aweme.music.ui.MusicDetailActivity",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.personalization.AdPersonalizationActivity",
                          "com.ss.android.ugc.aweme.host.TikTokHostActivity",
                          "com.bytedance.hybrid.spark.page.SparkActivity",
                          "com.ss.android.ugc.aweme.notification.MusNotificationDetailActivity",
                          "com.ss.android.ugc.aweme.im.sdk.chat.ui.powerpage.SelectChatMsgHostActivity",
                          "com.ss.android.ugc.aweme.account.login.auth.I18nSignUpActivity",
                          "com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity",
                          "com.ss.android.ugc.aweme.search.pages.core.ui.activity.SearchResultActivity",
                          "com.ss.android.ugc.aweme.relation.ffp.ui.FindFriendsPageActivity",
                          "com.ss.android.ugc.aweme.im.sdk.relations.ui.activity.RelationSelectActivity",
                          "com.ss.android.ugc.aweme.setting.I18nSettingManageMyAccountActivity",
                          "com.ss.android.ugc.aweme.im.sdk.chatdetail.ui.activity.FriendChatDetailActivity",
                          "com.ss.android.ugc.aweme.splash.SplashActivity",
                          "com.bytedance.lobby.instagram.InstagramAuthActivity",
                          "com.ss.android.ugc.aweme.setting.ui.SettingContainerActivity",
                          "com.ss.android.ugc.aweme.watch.history.core.WatchHistoryActivity",
                          "com.ss.android.ugc.aweme.account.login.v2.ui.SignUpOrLoginActivity",
                          "com.ss.android.ugc.aweme.ecommerce.base.osp.page.OrderSubmitActivity",
                          "com.ss.android.ugc.aweme.wiki.AddWikiActivity",
                          "com.ss.android.ugc.trill.setting.ContentPreferenceActivity",
                          "com.ss.android.ugc.aweme.shortvideo.mvtemplate.choosemedia.MvChoosePhotoActivity",
                          "com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity",
                          "com.ss.android.ugc.aweme.mix.videodetail.MixVideoDetailActivity",
                          "com.ss.android.ugc.aweme.creatortools.CreatorToolsActivity",
                          "com.ss.android.ugc.aweme.journey.NewUserJourneyActivity",
                          "com.ss.android.ugc.aweme.profile.ui.ProfileEditActivity",
                          "com.ss.android.ugc.aweme.following.ui.FollowRelationTabActivity",
                          "com.ss.android.ugc.aweme.shortvideo.edit.VEVideoPublishEditActivity",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.advertiser.AdvertiserSettingsActivity"}
    assert set(response.json()["last_debloated_activities"]) == set()


def test_debloat_activity():
    request = client.build_request(method="POST",
                                   url="/debloat_activity",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24", "activity_names": "org.woheller69.spritpreise.activities.ManageLocationsActivity,org.woheller69.spritpreise.activities.AboutActivity"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    assert set(response.json()["to_remove_methods"]) == {"<org.woheller69.spritpreise.activities.ManageLocationsActivity: void onDestroy()>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: void <init>()>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: void addCityToList(org.woheller69.spritpreise.database.City)>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: org.woheller69.spritpreise.database.CityToWatch convertCityToWatched(org.woheller69.spritpreise.database.City)>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: void onCreate(android.os.Bundle)>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: void onResume()>",
         "<org.woheller69.spritpreise.activities.ManageLocationsActivity: int getNavigationDrawerID()>",
         "<org.woheller69.spritpreise.activities.AboutActivity: void onCreate(android.os.Bundle)>",
         "<org.woheller69.spritpreise.activities.AboutActivity: void <init>()>",
         "<org.woheller69.spritpreise.activities.AboutActivity: int getNavigationDrawerID()>"}
    assert set(response.json()["to_remove_permissions"]) == set()
    request = client.build_request(method="POST",
                                   url="/debloat_activity",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010", "activity_names": "com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity,com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity"},
                                   headers={"Authorization": f"Bearer {access_token}"},
                                   )
    response = client.send(request)
    assert response.status_code == 200
    assert set(response.json()["to_remove_methods"]) == {"<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onResume()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onPause()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onSaveInstanceState(android.os.Bundle)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: boolean dJ_()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZJ(X.GcK)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZ(com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void finish()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZ(boolean)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onRestoreInstanceState(android.os.Bundle)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZ(X.GcL)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZIZ(X.GcL)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onStop()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onDestroy()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LJII()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZIZ(boolean)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: boolean LIZ(android.content.Intent)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void <init>()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void LIZIZ(X.GcK)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onCreate(android.os.Bundle)>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: android.content.Intent getIntent()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: X.X6W getInflater()>",
         "<com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity: void onStart()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onCreate(android.os.Bundle)>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: java.lang.String getBtmPageCode()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onStart()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onResume()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void <init>()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onDestroy()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: android.content.Intent getIntent()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onPause()>",
         "<com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity: void onStop()>"}
    assert set(response.json()["to_remove_permissions"]) == set()


def test_get_acitivities_after_debloated():
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "org.woheller69.spritpreise", "version_code": "24"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"org.woheller69.spritpreise.activities.AboutActivity",
                          "org.woheller69.spritpreise.firststart.TutorialActivity",
                          "org.woheller69.spritpreise.activities.ManageLocationsActivity",
                          "org.woheller69.spritpreise.activities.SettingsActivity",
                          "org.woheller69.spritpreise.activities.CityGasPricesActivity"}
    assert set(response.json()["last_debloated_activities"]) == {
        "org.woheller69.spritpreise.activities.ManageLocationsActivity",
        "org.woheller69.spritpreise.activities.AboutActivity"}
    request = client.build_request(method="POST",
                                   url="/get_acitivities",
                                   params={"package_name": "com.zhiliaoapp.musically", "version_code": "2022903010"},
                                   headers={"Authorization": f"Bearer {access_token}"}
                                   )
    response = client.send(request)
    assert response.status_code == 200
    actitivies = set(response.json()["activities"])
    assert actitivies == {"com.ss.android.ugc.aweme.livewallpaper.ui.LocalLiveWallPaperActivity",
                          "com.ss.android.ugc.aweme.ecommerce.showcase.showcase.ShowcaseActivity",
                          "com.ss.android.ugc.aweme.share.qrcode.UserQRCodeActivity",
                          "com.ss.android.ugc.aweme.crossplatform.activity.CrossPlatformActivity",
                          "com.ss.android.ugc.aweme.compliance.business.filtervideo.ui.activity.FilterVideoKeywordsActivity",
                          "com.ss.android.ugc.aweme.ecommerce.base.pdp.ui.PdpActivity",
                          "com.ss.android.ugc.aweme.detail.ui.DetailActivity",
                          "com.ss.android.ugc.aweme.qrcode.view.ScanQRCodeActivityV2",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.inference.AdInferenceActivity",
                          "com.ss.android.ugc.aweme.live.LivePlayActivity",
                          "com.ss.android.ugc.aweme.setting.ui.PushSettingNotificationChoiceActivity",
                          "com.ss.android.ugc.aweme.music.ui.MusicDetailActivity",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.personalization.AdPersonalizationActivity",
                          "com.ss.android.ugc.aweme.host.TikTokHostActivity",
                          "com.bytedance.hybrid.spark.page.SparkActivity",
                          "com.ss.android.ugc.aweme.notification.MusNotificationDetailActivity",
                          "com.ss.android.ugc.aweme.im.sdk.chat.ui.powerpage.SelectChatMsgHostActivity",
                          "com.ss.android.ugc.aweme.account.login.auth.I18nSignUpActivity",
                          "com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity",
                          "com.ss.android.ugc.aweme.search.pages.core.ui.activity.SearchResultActivity",
                          "com.ss.android.ugc.aweme.relation.ffp.ui.FindFriendsPageActivity",
                          "com.ss.android.ugc.aweme.im.sdk.relations.ui.activity.RelationSelectActivity",
                          "com.ss.android.ugc.aweme.setting.I18nSettingManageMyAccountActivity",
                          "com.ss.android.ugc.aweme.im.sdk.chatdetail.ui.activity.FriendChatDetailActivity",
                          "com.ss.android.ugc.aweme.splash.SplashActivity",
                          "com.bytedance.lobby.instagram.InstagramAuthActivity",
                          "com.ss.android.ugc.aweme.setting.ui.SettingContainerActivity",
                          "com.ss.android.ugc.aweme.watch.history.core.WatchHistoryActivity",
                          "com.ss.android.ugc.aweme.account.login.v2.ui.SignUpOrLoginActivity",
                          "com.ss.android.ugc.aweme.ecommerce.base.osp.page.OrderSubmitActivity",
                          "com.ss.android.ugc.aweme.wiki.AddWikiActivity",
                          "com.ss.android.ugc.trill.setting.ContentPreferenceActivity",
                          "com.ss.android.ugc.aweme.shortvideo.mvtemplate.choosemedia.MvChoosePhotoActivity",
                          "com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity",
                          "com.ss.android.ugc.aweme.mix.videodetail.MixVideoDetailActivity",
                          "com.ss.android.ugc.aweme.creatortools.CreatorToolsActivity",
                          "com.ss.android.ugc.aweme.journey.NewUserJourneyActivity",
                          "com.ss.android.ugc.aweme.profile.ui.ProfileEditActivity",
                          "com.ss.android.ugc.aweme.following.ui.FollowRelationTabActivity",
                          "com.ss.android.ugc.aweme.shortvideo.edit.VEVideoPublishEditActivity",
                          "com.bytedance.ies.ugc.aweme.commercialize.compliance.advertiser.AdvertiserSettingsActivity"}
    assert set(response.json()["last_debloated_activities"]) == {
        "com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity",
        "com.ss.android.ugc.aweme.ecommerce.showcase.store.StoreActivity"}
