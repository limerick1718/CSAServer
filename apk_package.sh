#package: name='cf.playhi.freezeyou' versionCode='149' versionName='11.3.149.20220512-gh' platformBuildVersionName='12' platformBuildVersionCode='32' compileSdkVersion='32' compileSdkVersionCodename='12'
package=$(aapt dump badging "$*" | awk '/package/{gsub("name=|'"'"'","");  print $2}')
versionCode=$(aapt dump badging "$*" | awk '/package/{gsub("versionCode=|'"'"'","");  print $3}')
#echo
#echo "   file : $1"
#echo "package : $package"
#echo "version : $versionCode"
echo "$package-$versionCode"