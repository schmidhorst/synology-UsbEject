#!/bin/bash
# Filename: logfile.cgi - coded in utf-8
#    taken from
#  DSM7DemoSPK (https://github.com/toafez/DSM7DemoSPK) and adopted to UsbEject by Horst Schmid
#        Copyright (C) 2022 by Tommes
# Member of the German Synology Community Forum

#             License GNU GPLv3
#   https://www.gnu.org/licenses/gpl-3.0.html

# This index.cgi is in the config file configured as "url": "/webman/3rdparty/<appName>/index.cgi"
# /usr/syno/synoman/webman/3rdparty/<app> is linked to /volumeX/@apptemp/<app>/ui
# and /var/packages/<app>/target/ui is the same folder

# for https://www.shellcheck.net/
# shellcheck disable=SC1090

# Initiate system
# --------------------------------------------------------------
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/syno/bin:/usr/syno/sbin
bDebug=0
if [[ -z "$SCRIPT_NAME" ]]; then  # direct start in debug run
  SCRIPT_NAME="/webman/3rdparty/UsbEject/logfile.cgi"
  bDebug=1
  echo "###### logfile.cgi executed in debug mode!!  ######"
fi
  # $0=/usr/syno/synoman/webman/3rdparty/<appName>/logfile.cgi
app_link=${SCRIPT_NAME%/*} # "/webman/3rdparty/<appName>"
app_name=${app_link##*/} # "<appName>"
  # DOCUMENT_URI=/webman/3rdparty/<appName>/logfile.cgi
  # PWD=/volume1/@appstore/<appName>/ui
user=$(whoami) # EnvVar $USER may be not well set, user is '<appName>'
  # REQUEST_URI=/webman/3rdparty/<appName>/logfile.cgi
  # SCRIPT_FILENAME=/usr/syno/synoman/webman/3rdparty/<appName>/logfile.cgi
display_name="USB Eject Tool for non-admin Users" # used as title of Page
LOG="/var/tmp/${app_name}.log"  # no permission if default -rw-r--r-- root:root was not changed
DTFMT="+%Y-%m-%d %H:%M:%S" # may be overwritten by parse_hlp
# $SHELL' is here "/sbin/nologin"
echo -e "\n$(date "$DTFMT"): App '$app_name' file '$0' started as user '$user' with parameters '$QUERY_STRING' ..." >> "$LOG"
# $0=/usr/syno/synoman/webman/3rdparty/<appName>/logfile.cgi
ah="/volume*/@appstore/$app_name/ui"
# SYNOPKG_PKGDEST_VOL
app_home=$(find $ah -maxdepth 0 -type d) # Attention: find is not working with quoted path!!

# env >> LOG"

# Load urlencode and urldecode function from ../modules/parse_hlp.sh:
if [ -f "${app_home}/modules/parse_hlp.sh" ]; then
  source "${app_home}/modules/parse_hlp.sh"
  res=$?
  echo "$(date "$DTFMT"): Loading ${app_home}/modules/parse_hlp.sh with functions urlencode() and urldecode() done with result $res" >> "$LOG"
  if [[ "$res" -gt 1 ]]; then
    echo "### Loading ${app_home}/modules/parse_hlp.sh failed!! ###"
    exit
  fi
else
  echo "$(date "$DTFMT"): Failed to find ${app_home}/modules/parse_hlp.sh with functions urlencode() and urldecode() skipped" >> "$LOG"
  echo "Failed to find ${app_home}/modules/parse_hlp.sh"
  exit
fi

# Evaluate app authentication
# To evaluate the SynoToken, change REQUEST_METHOD to GET
# Read out and check the login authorization  ( login.cgi )
if [[ "$bDebug" -eq 0 ]]; then
  cgiLogin # see parse_hlp.sh, sets $syno_login, $syno_token, $syno_user, $is_admin
  ret=$?
  if [[ "$ret" -ne "0" ]]; then
    exit
  fi
else
  echo "Due to debug mode login skipped"
fi

# get the installed version of the package for later comparison to latest version on github:
local_version=$(cat "/var/packages/${app_name}/INFO" | grep ^version | cut -d '"' -f2)

if [ -x "${app_home}/modules/parse_language.sh" ]; then
  source "${app_home}/modules/parse_language.sh" "${syno_user}"
  res=$?
  logInfoNoEcho 7 "Loading ${app_home}/modules/parse_language.sh done with result $res"
  # || exit
else
  logInfo 1 "Loading ${app_home}/modules/parse_language.sh failed"
  exit
fi
# ${used_lang} is now setup, e.g. enu

# Resetting access permissions
unset syno_login rar_data syno_privilege syno_token syno_user user_exist is_authenticated
declare -A get # associative array for parameters (POST, GET)

# Evaluate app authentication
if [[ "$bDebug" -eq 0 ]]; then
  evaluateCgiLogin #
  ret=$?
  if [[ "$ret" -ne "0" ]]; then
    exit
  fi
else
  echo "Due to debug mode access check skipped"
  is_admin="yes"
fi

# Set variables to "readonly" for protection or empty contents
unset syno_login rar_data syno_privilege
readonly syno_token syno_user user_exist is_admin # is_authenticated

licenceFile="licence_${used_lang}.html"
if [[ ! -f "licence_${used_lang}.html" ]]; then
  licenceFile="licence_enu.html"
fi

if [ "$is_admin" != "yes" ]; then
  echo "Content-type: text/html"
  echo
  echo "<!doctype html><html lang=\"${SYNO2ISO[${used_lang}]}\">"
  echo "<HEAD><TITLE>$app_name: ${LoginRequired}</TITLE></HEAD><BODY>${PleaseLogin}<br/>"
  echo "<button onclick=\"location.href='$licenceFile'\" type=\"button\">${btnShowLicence}</button> "

  echo "<br/></BODY></HTML>"
  logInfoNoEcho 1 "Admin Login required!"
  echo "Admin Login required!"
  exit 0
fi

#appCfgDataPath=$(find /volume*/@appdata/${app_name} -maxdepth 0 -type d)
appCfgDataPath="/var/packages/${app_name}/var"
if [ ! -d "${appCfgDataPath}" ]; then
  logInfo 1 "logfile.cgi: app home folder '$appCfgDataPath' not found!"
  echo "$(date "$DTFMT"): ls -l /:" >> "$LOG"
  ls -l / >> "$LOG"
  # exit
fi

# Set environment variables
# --------------------------------------------------------------
# Set up folder for temporary data:
app_temp="${app_home}/temp" # /volume*/@appstore/${app_name}/ui/temp
#  or /volume*/@apptemp/$app_name ?? SYNOPKG_PKGDEST_VOL
if [ ! -d "${app_temp}" ]; then
  mkdir -p -m 755 "${app_temp}"
fi
# result="${app_temp}/result.txt"

# Evaluate POST and GET requests and cache them in files
  # get_keyvalue="/bin/get_key_value"

# Processing GET/POST request variables
# CONTENT_LENGTH: CGI meta variable https://stackoverflow.com/questions/59839481/what-is-the-content-length-varaible-of-a-cgi

SCRIPT_EXEC_LOG="$appCfgDataPath/execLog"
logfile="$SCRIPT_EXEC_LOG" # default, later optionally set to "$appCfgDataPath/detailLog"
pageTitle=$(echo "$logTitleExec")  # default, later optionally set to "$logTitleDetail"


# Analyze incoming POST requests and process them to ${get[key]}="$value" variables
cgiDataEval 


if [[ "$logfile" == "$appCfgDataPath/detailLog" ]]; then
  pageTitle=$(echo "$logTitleDetail") # read it again and insert the changed LOGLEVEL
fi
script='<script language="javascript"> '
script="$script function resizeWindow(){ resizeTo(250,200); window.focus(); };"
if [[ -n "${get[action]}" ]]; then
  val="${get[action]}"
  if [[ "$val" == "showDetailLog" ]] || [[ "$val" == "delDetailLog" ]] || [[ "$val" == "reloadDetailLog" ]] || [[ "$val" == "downloadDetailLog" ]] || [[ "$val" == "chgDetailLogLevel" ]] || [[ "$val" == "SupportEMail" ]]; then
    logfile="$appCfgDataPath/detailLog"  # Link to /var/tmp/autorun.log
    pageTitle=$(echo "$logTitleDetail") # with actual LOGLEVEL
  fi
  if [[ "$val" == "delSimpleLog" ]] || [[ "$val" == "delDetailLog" ]]; then
    echo "" > "$logfile"
    logInfoNoEcho 4 "Old content of '$logfile' removed"
  fi
  if [[ "$val" == "downloadSimpleLog" ]] || [[ "$val" == "downloadDetailLog" ]]; then
    logInfoNoEcho 4 "Download content of '$logfile' requested, disposition='$disposition'"
    echo "Content-type: text/plain; charset=utf-8"
    echo "Content-Disposition: attachment; filename=$(basename "$logfile").txt"
    echo
    # echo "<!doctype html>"
    cat "$logfile"
    if [[ "$val" == "downloadDetailLog" ]]; then
      echo -e "\n"
      env || printenv
      echo ""
      # lets append the content of $SCRIPT_EXEC_LOG for full debug info:
      cat "$SCRIPT_EXEC_LOG"
    fi
    exit
  fi
  if [[ "$val" == "chgDetailLogLevel" ]]; then
    newlevel=$(echo "${get[logNewlevel]}" | grep "[1-8]")
    if [[ -n "$newlevel" ]]; then
      if [[ -f "$appCfgDataPath/config" ]]; then
        res="$(sed -i "s|^LOGLEVEL=.*$|LOGLEVEL=\"$newlevel\"|" "$appCfgDataPath/config")"
        result=$?
        logInfoNoEcho 4 "logfile.cgi LogLevel change to '$newlevel' in file '$appCfgDataPath/config': result='$result', res='$res'"
        LOGLEVEL="$newlevel"
        # $logTitleDetail and pageTitle has still old loglevel:
     	  eval "$(grep "logTitleDetail=" "$lngFile")" # lngfile was set in parse_language.sh to texts/${used_lang}/lang.txt
        pageTitle="$logTitleDetail"
      fi
    fi
  fi

  if [[ "$val" == "reloadSimpleLog" ]] || [[ "$val" == "reloadDetailLog" ]]; then
    logInfoNoEcho 7 "Page reload"
    script="${script} function scrollDown(){ window.scrollTo(0, document.body.scrollHeight);};"  # scroll to bottom

# https://stackoverflow.com/questions/17642872/refresh-page-and-keep-scroll-position
# not working:
#       script="${script} window.addEventListener(\"beforeunload\", function (e) { sessionStorage.setItem('scrollpos', window.scrollY); });"
#       script="${script} window.onload=function(){
#         var scrollpos = sessionStorage.getItem('scrollpos');
#         if (scrollpos) {
#           window.scrollTo(0, scrollpos);
#           sessionStorage.removeItem('scrollpos');
#           };
#         }"

  fi # reload
fi # action

script="${script} </script> "
linkTarget="$(readlink "$logfile")" # result 1 if it's not a link
if [[ "$?" -eq "0" ]]; then
  filesize_Bytes=$(stat -c%s "$linkTarget")
  lineCount=$(wc -l < "$linkTarget")
else
  filesize_Bytes=$(stat -c%s "$logfile")  # if it's a link this returns size of the link, not of linked file!
  lineCount=$(wc -l < "$logfile")
fi
logInfoNoEcho 8 "Size of $logfile is $lineCount lines, $filesize_Bytes Bytes"
if [[ "$bDebug" -ne 0 ]]; then
  echo "starting to generate html document ..."
fi
# Layout output
# --------------------------------------------------------------
if [ $(synogetkeyvalue /etc.defaults/VERSION majorversion) -ge 7 ]; then
  echo "Content-type: text/html; charset=utf-8"
  echo
  echo "
  <!doctype html>
  <html lang=\"${SYNO2ISO[${used_lang}]}\">
    <head>"
  echo '<meta charset="utf-8" />'
  # echo "<title>${pageTitle}</title>"   # <title>...</title> is not displayed but title from the file config
  echo '
      <link rel="shortcut icon" href="images/icon_32.png" type="image/x-icon" />
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
      <link rel="stylesheet" type="text/css" href="dsm3.css"/>'
  echo "$script"
  echo '</head>
    <body onload="resizeWindow(); scrollDown()">
      <header>'
        # Load page content
        if [[ "$is_admin" == "yes" ]]; then
          echo "<button onclick=\"location.href='index.cgi'\" type=\"button\">${btnBackToMainPage}</button> "
          if [[ "$logfile" == "$SCRIPT_EXEC_LOG" ]]; then
            echo "<button onclick=\"location.href='logfile.cgi?action=showDetailLog'\" type=\"button\">${btnShowDetailLog}</button> "
          else
            echo "<button onclick=\"location.href='logfile.cgi'\" type=\"button\">${btnShowActionLog}</button> "
          fi
          echo "<button onclick=\"location.href='settings.cgi'\" type=\"button\">${btnShowSettings}</button> "
          echo "<button onclick=\"location.href='$licenceFile'\" type=\"button\">${btnShowLicence}</button> "
          echo "<p><strong>$pageTitle</strong></p></header><table>"

          if [[ -f "$logfile" ]]; then
            if [[ filesize_Bytes -lt 10 ]]; then
              msg=$(echo "$execLogNA")
              echo "<tr><td>$msg</td></tr>"
            else
              while read line; do # read all items from logfile
                timestamp=${line%%: *}
                msg=${line#*: }
                if [[ "$msg" == "$timestamp" ]]; then # no ": "
                  timestamp="" # put all to 2nd column
                fi
                echo "<tr><td>$timestamp</td><td>$msg</td></tr>"
              done < "$logfile" # Works well even if last line has no \n!
            fi
          else
            logInfoNoEcho 3 "'$logfile' not found!"
            logInfoNoEcho 8 "execLogNA='$execLogNA'"
            msg=$(echo "$execLogNA")
            echo "<tr><td>$msg</td></tr>"
          fi
        else
          # Infotext: Access allowed only for users from the Administrators group
          echo '<p>'${txtAlertOnlyAdmin}'</p>'
        fi
        echo '
      </table>
      <p style="margin-left:22px; line-height: 16px;">'

      if [[ "$logfile" == "$SCRIPT_EXEC_LOG" ]]; then
        echo "<button onclick=\"location.href='logfile.cgi?action=reloadSimpleLog'\" type=\"button\">${btnRefresh}</button> "
        if [[ filesize_Bytes -gt 10 ]]; then
          echo "<button onclick=\"location.href='logfile.cgi?action=downloadSimpleLog'\" type=\"button\">${btnDownload}</button> "
          echo "<button onclick=\"location.href='logfile.cgi?action=delSimpleLog'\" type=\"button\">${btnDelLog}</button> "
        fi # if [[ filesize_Bytes -gt 10 ]]
      else # detailed debug log: Allow to change the LOGLEVEL:
        echo "<form action='logfile.cgi?action=chgDetailLogLevel' method='post'>
              <label for='fname'>LogLevel:</label>
              <select name='logNewlevel' id='logNewlevel'>"
        for ((i=1; i<=8; i+=1)); do
          if [[ "$i" -eq "$LOGLEVEL" ]]; then
            echo "<option selected>$i</option>"
          else
            echo "<option>$i</option>"
          fi
        done
        echo "</select>"
        echo "<input type='submit' value='Submit'>&nbsp;&nbsp;&nbsp;"
        # also inside the <form ...> to have it in the same row:
        echo "<button onclick=\"location.href='logfile.cgi?action=reloadDetailLog'\" type=\"button\">${btnRefresh}</button>&nbsp;  "
        if [[ filesize_Bytes -gt 10 ]]; then
          echo "<button onclick=\"location.href='logfile.cgi?action=downloadDetailLog'\" type=\"button\">${btnDownload}</button>&nbsp; "
          echo "<button onclick=\"location.href='logfile.cgi?action=delDetailLog'\" type=\"button\">${btnDelLog}</button> "
          # echo "<button onclick=\"location.href='logfile.cgi?action=SupportEMail'\" type=\"button\">Send Support-eMail</button> "
        fi # if [[ filesize_Bytes -gt 10 ]]
        echo "</form>"

      fi # if [[ "$logfile" == "$SCRIPT_EXEC_LOG" ]] else
      echo "</p>
        </body>
      </html>"
fi # if [ $(synogetkeyvalue /etc.defaults/VERSION majorversion) -ge 7 ]
logInfoNoEcho 4 "$(basename "$0") done"
exit

