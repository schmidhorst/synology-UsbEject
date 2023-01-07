#!/bin/bash
# Filename: index.cgi - coded in utf-8
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
  SCRIPT_NAME="/webman/3rdparty/UsbEject/index.cgi"
  bDebug=1
  echo "###### index.cgi executed in debug mode!!  ######"
fi
  # $0=/usr/syno/synoman/webman/3rdparty/<appName>/index.cgi
app_link=${SCRIPT_NAME%/*} # "/webman/3rdparty/<appName>"
app_name=${app_link##*/} # "<appName>"
  # DOCUMENT_URI=/webman/3rdparty/<appName>/index.cgi
  # PWD=/volume1/@appstore/<appName>/ui
user=$(whoami) # EnvVar $USER may be not well set, user is '<appName>'
  # REQUEST_URI=/webman/3rdparty/<appName>/index.cgi
  # SCRIPT_FILENAME=/usr/syno/synoman/webman/3rdparty/<appName>/index.cgi
# display_name="USB Eject Tool for non-admin Users" # used as title of Page
LOG="/var/tmp/${app_name}.log"  # no permission if default -rw-r--r-- root:root was not changed
DTFMT="+%Y-%m-%d %H:%M:%S" # may be overwritten by parse_hlp
# $SHELL' is here "/sbin/nologin"
echo -e "\n$(date "$DTFMT"): App '$app_name' file '$(basename "$0")' started with parameters '$QUERY_STRING' ..." >> "$LOG"
# $0=/usr/syno/synoman/webman/3rdparty/<appName>/index.cgi
ah="/volume*/@appstore/$app_name/ui"
# SYNOPKG_PKGDEST_VOL
app_home=$(find $ah -maxdepth 0 -type d) # Attention: find is not working with quoted path!!

# Load urlencode and urldecode, logInfo, ... function from ../modules/parse_hlp.sh:
if [ -f "${app_home}/modules/parse_hlp.sh" ]; then
  source "${app_home}/modules/parse_hlp.sh"
  res=$?
  # echo "$(date "$DTFMT"): Loading parse_hlp.sh with functions urlencode() and urldecode() done with result $res" >> "$LOG"
  if [[ "$res" -gt 1 ]]; then
    echo "### Loading ${app_home}/modules/parse_hlp.sh failed!! res='$res' ###" >> "$LOG"
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
    echo "$(date "$DTFMT"): $(basename "$0"), calling cgiLogin failed, ret='$ret' " >> "$LOG"
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
  logInfoNoEcho 7 "$(basename "$0"), Loading ${app_home}/modules/parse_language.sh done with result $res"
  # || exit
else
  logInfo 1 "Loading ${app_home}/modules/parse_language.sh failed"
  exit
fi
# ${used_lang} is now setup, e.g. enu

# Resetting access permissions
unset syno_login rar_data syno_privilege syno_token user_exist is_authenticated
declare -A get # associative array for parameters (POST, GET)

# Evaluate app authentication
if [[ "$bDebug" -eq 0 ]]; then
  evaluateCgiLogin # in parse_hlp.sh
  ret=$?
  if [[ "$ret" -ne "0" ]]; then
    logInfo 1 "$(basename "$0"), execution of evaluateCgiLogin failed, ret='$ret'"
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

#appCfgDataPath=$(find /volume*/@appdata/${app_name} -maxdepth 0 -type d)
appCfgDataPath="/var/packages/${app_name}/var"
if [ ! -d "${appCfgDataPath}" ]; then
  logInfo 1 "$(basename "$0"), app var folder '$appCfgDataPath' not found!"
  # exit
fi
appTmpPath="/var/packages/${app_name}/tmp"
if [ ! -d "${appTmpPath}" ]; then
  logInfo 1 "$(basename "$0"), app tmp folder '$appTmpPath' not found!"
  # exit
fi

SCRIPT_EXEC_LOG="$appCfgDataPath/execLog"
logfile="$SCRIPT_EXEC_LOG" # default, later optionally set to "$appCfgDataPath/detailLog"
pageTitle="$indexCgiTitle"  # default, later optionally extended"
if [[ "$is_admin" == "yes" ]]; then
  pageTitle="$pageTitle, $indexCgiTitleAdminExt"
fi

# Analyze incoming POST requests and process them to ${get[key]}="$value" variables
cgiDataEval # parse_hlp.sh, setup associative array get[] from the request (POST and GET)

versionUpdateHint=""
githubRawInfoUrl="https://raw.githubusercontent.com/schmidhorst/synology-UsbEject/main/INFO.sh" #patched to distributor_url from INFO.sh
 # above line will be patched from INFO.sh and is used to check for a newer version
if [[ -n "$githubRawInfoUrl" ]]; then
  git_version=$(wget --timeout=30 --tries=1 -q -O- "$githubRawInfoUrl" | grep ^version | cut -d '"' -f2)
  logInfoNoEcho 6 "index.cgi, local_version='$local_version', git_version='$git_version'"
  if [ -n "${git_version}" ] && [ -n "${local_version}" ]; then
    if dpkg --compare-versions "${git_version}" gt "${local_version}"; then
    # if dpkg --compare-versions ${git_version} lt ${local_version}; then # for debugging
      vh=$(echo "$update_available")
      versionUpdateHint='<p style="text-align:center">'${vh}' <a href="https://github.com/schmidhorst/synology-'${app_name}'/releases" target="_blank">'${git_version}'</a></p>'
    fi
  fi
fi
notAllowed=""
if [[ "${get[action]}" == "filter" ]]; then
  if [[ "$is_admin" == "yes" ]]; then
    val="${get[expr]}"
    if [[ -n "$val" ]]; then
      ### open issue: how could the syntax be checked to avoid code injection by the user? ###
      ### which characters should be not allowed? Or only in special combinations?
      if [[ "${#val}" -gt 30 ]]; then
        notAllowed="Error: Filter string too long!" # don't allow long injection code
      elif [[ "${val}" == *':'* ]]; then
        notAllowed="Error: ':' is not allowed in the filter string" # don't allow long injection code, e.g. https://en.wikipedia.org/wiki/Fork_bomb
        # Reg expr (?:x) = Non-capturing group is the only known systax, where : would be required
      else
        # set filter
        val="${val//\./\\\.}"
        val="${val//|/\\\|}"
        logInfoNoEcho 7 "dot-escape added: '$val'"
        if [[ -n "$(grep "^FILTER=" "$appCfgDataPath/config")" ]]; then
          sed -i "s|^FILTER=.*\$|FILTER=\"${val//$/\\$}\"|" "$appCfgDataPath/config"
        else
          echo "FILTER=\"${val//$/\\$}\"" >> "$appCfgDataPath/config" # escape all $ signs
        fi
      fi
    else
      #delete filter
      sed -i "s|^FILTER=.*\$|FILTER=\"\"|" "$appCfgDataPath/config"
    fi
  else # suspicious!! Non-admin user cannot send the action=filter in normal way!
    logInfoNoEcho 1 "===== Alert!! ${app_name} $(basename "$0"), Received a new value for the filter to hide some drives from non-admin user ${syno_user} ====="
    logInfoNoEcho 1 "===== Alert!! It looks like that user tries to penetrate the system ====="
    # dsmnotify ?
    # sendmail ?
  fi
  val="${get[expr]}"
  logInfoNoEcho 7 "action='filter', expr='$val'"
fi # action filter change

line="$(grep "FILTER=" "$appCfgDataPath/config")"
# eval "$line" would be a security risk as the string was a user input!
FILTER="$(sed -e 's/^\"//' -e 's/\"$//' <<<"${line#*=}")" # Extract part behind '=' and remove quotes
# e.g. https://en.wikipedia.org/wiki/Fork_bomb
FILTER2=$(echo "$FILTER" | sed 's/\$/\\\$/g')
# whats about the '|' e.g. for (<part1>)|(<part2>)
logInfoNoEcho 7 "FILTER='$FILTER', FILTER2='$FILTER2'"

if [[ "${get[action]}" == "reloadActionLog" ]]; then
  logInfoNoEcho 7 "index.cgi, Page reload"
fi # reload

linkTarget="$(readlink "$logfile")" # result 1 if it's not a link
if [[ "$?" -eq "0" ]]; then
  filesize_Bytes=$(stat -c%s "$linkTarget")
  lineCount=$(wc -l < "$linkTarget")
else
  filesize_Bytes=$(stat -c%s "$logfile")  # if it's a link this returns size of the link, not of linked file!
  lineCount=$(wc -l < "$logfile")
fi
logInfoNoEcho 8 "index.cgi, Size of $logfile is $lineCount lines, $filesize_Bytes Bytes"
if [[ "$bDebug" -ne 0 ]]; then
  echo "starting to generate html document ..."
fi

# extdisks=$(/usr/syno/bin/synousbdisk -enum) # no permission
# logInfoNoEcho 8 "Result from 'synousbdisk -enum': $extdisks"
extDiskCount=0
appTmpPath="/var/packages/${app_name}/tmp"
myLS=$(ls -l "$appTmpPath"/*)
logInfoNoEcho 8 "index.cgi, myLS='$myLS'"
declare -A diskArray
oldShopt=$(shopt -p nullglob)
shopt -s nullglob # do not return the mask if the folder is empty
autoRefresh=0
for myFile in "$appTmpPath/"*; do
  bn="$(basename "$myFile")"
  if [[ "$bn" == *"_ejecting" ]]; then
    autoRefresh=1
    logInfoNoEcho 4 "index.cgi, Refresh due to '$bn'"
  elif [[ "$bn" == *"__"* ]]; then
    autoRefresh=1
    logInfoNoEcho 4 "index.cgi, Refresh due to '$bn'"
  fi
  value=$(<"$myFile")
  logInfoNoEcho 5 "index.cgi, file '$myFile' (${bn%%_*}), content: '$value'"
  diskArray[${bn%%_*}]="$value" # e.g. diskArray[usb1p1]="usbshare1:/volumeUSB1/usbshare/:Seagate Expansion HDD 00000000NXZ000N"
  logInfoNoEcho 5 "index.cgi, diskArray[${bn%%_*}]='${diskArray[${bn%%_*}]}'"
done
$oldShopt
extDiskCount=${#diskArray[@]}
logInfoNoEcho 5 "Found $extDiskCount disks: ${diskArray[*]}, oldShopt='$oldShopt'"

if [[ -z "${get[action]}" ]]; then
  logInfoNoEcho 4 "index.cgi without an action"
else
  logInfoNoEcho 4 "index.cgi with action='${get[action]}'"
fi
if [[ "${get[action]}" == "eject" ]] && [[ "$autoRefresh" -eq "0" ]]; then
  if [[ -n ${get[umount]} ]]; then # e.g.  get[umount]='usb1p1'
    logInfoNoEcho 4 "index.cgi, found: get[action]='${get[action]}' and get[umount]='${get[umount]}', "
    # Append ${syno_user} to the file name
    oldName="$appTmpPath/${get[umount]}"
    mv "$oldName" "${oldName}__${syno_user}"
    logInfoNoEcho 6 "index.cgi, Eject: file '$oldName' renamed to '${oldName}__${syno_user}'"
    if [[ -f "${oldName}" ]] || [[ -n "$(ls -A "${oldName}_"*)" ]]; then # only if the file with the name ${get[umount]} still exists
      autoRefresh=1
    fi
    logInfoNoEcho 4 "index.cgi, Refresh due to umount '${get[umount]}'"
  else
    logInfoNoEcho 4 "index.cgi, action=eject but missing 'umount' parameter with dev info"
  fi # umount
fi # if [[ "${get[action]}" == "eject" ]]

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
  if [[ "$autoRefresh" -ne "0" ]]; then
    echo '<meta http-equiv="refresh" content="1" >'
  fi
  # echo "<title>${pageTitle}</title>"   # <title>...</title> is not displayed but title from the file config
  echo '
      <link rel="shortcut icon" href="images/icon_32.png" type="image/x-icon" />
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" /> '
  echo '  <link rel="stylesheet" type="text/css" href="dsm3.css"/>'
  echo '<style>
         th, td {
         padding: 8px;
         }
        </style>'
  # echo "$script"
  echo '</head>
    <body>
      <header>'
  echo "$versionUpdateHint"
        # Load page content
        if [[ "$is_admin" == "yes" ]]; then
          echo "<button onclick=\"location.href='logfile.cgi?action=showActionLog'\" type=\"button\">${btnShowActionLog}</button> "
          echo "<button onclick=\"location.href='logfile.cgi?action=showDetailLog'\" type=\"button\">${btnShowDetailLog}</button> "
        fi
        echo "<button onclick=\"location.href='$licenceFile'\" type=\"button\">${btnShowLicence}</button> "
        echo "<p><strong>$pageTitle</strong></p></header><table>"

        if [[ "$is_admin" == "yes" ]]; then
          echo "<tr><th>Dev</th><th>Share</th><th>Mount</th><th>Name</th><th>Port</th><th>Eject</th><th>non admin</th></tr>"
        fi
        counter=0
        for disk in "${!diskArray[@]}"; do
          logInfoNoEcho 4 "disk='$disk', diskArray[${disk}]='${diskArray[${disk}]}'"
          mapfile -d ":" -t items  < <(/bin/printf '%s' "${diskArray[${disk}]}") # disk is the key of the element of the associative array
          # e.g. disk="usb1p1", items[0]="usbshare12", items[1]="/volumeUSB12/usbshare/", items[2]="Seagate Expansion HDD 00000000NXZ000N", items[3]="2-2.2"
          literal=";${disk%%_*};${items[0]};${items[1]};${items[2]};${items[3]};"
          if [[ "$is_admin" == "yes" ]]; then
            ((counter+=1))
            if [[ -z "$FILTER" ]]; then
              marker=""
            elif [[ "$literal" =~ $FILTER ]]; then
              marker="$indexCgiHidden"
            else
              marker=" "
            fi
            if [[ "$autoRefresh" -eq "1" ]]; then
              echo "<tr><td>${disk%%_*}</td><td>${items[0]}</td><td>${items[1]}</td><td>${items[2]}</td><td>${items[3]}</td><td>Wait!</td><td>$marker</td></tr>"
            else
              echo "<tr><td>${disk%%_*}</td><td>${items[0]}</td><td>${items[1]}</td><td>${items[2]}</td><td>${items[3]}</td><td style='padding: 0px' style='text-align: center;'><button onclick=\"location.href='index.cgi?action=eject&umount=${disk}'\" type=\"button\" title=\"Eject\"><img src=\"images/eject_24.png\" alt='Eject'></button></td><td>$marker</td></tr>"
            fi
          elif [[ -z "$FILTER" ]] || [[ ! "$literal" =~ $FILTER ]]; then
            ((counter+=1))
            if [[ "$autoRefresh" -eq "1" ]]; then
              echo "<tr><td>${items[0]}</td><td>${items[2]}</td><td>$indexCgiWait</td></tr>"
            else
              echo "<tr><td>${items[0]}</td><td>${items[2]}</td><td style='padding: 0px'><button onclick=\"location.href='index.cgi?action=eject&umount=${disk}'\" type=\"button\" title=\"Eject\"><img src=\"images/eject_24.png\" alt='Eject' class='centerImage'></button></td></tr>"
            fi
          fi
        done


        if [[ "$counter" -eq "0" ]]; then
          if [[ -z "$indexCgiNoExtDisks" ]]; then # Fallback to english message
            indexCgiNoExtDisks="No external storage devices found which have been plugged in to the DSM after the start of the package ${app_name}"
          fi
          echo "<tr><td colspan='100%'>${indexCgiNoExtDisks}</td></tr>"
        fi
        echo '
      </table>'
    if [[ "$is_admin" == "yes" ]]; then
      echo "<p>$indexCgiFilter</p>"
      if [[ -n "$notAllowed" ]]; then
        echo "<p><span style='color:red'>Your entered filter string is not allowed: $notAllowed</span></p>"
      fi
      echo "<form action='index.cgi?action=filter' method='post'>
            <label for='expr'>$indexCgiFilterLabel:</label>
            <input type='text' id='expr' name='expr' value='$FILTER2'><input type='submit' value='   '>
            </form>"
    fi
    echo '
    <p style="margin-left:0px; line-height: 16px;">'
    if [[ "$autoRefresh" -eq "0" ]]; then
      echo "<button onclick=\"location.href='index.cgi?action=reloadDrives'\" type=\"button\">${btnRefresh}</button> "
    fi
    echo "</p></body>
    </html>"
fi # if [ $(synogetkeyvalue /etc.defaults/VERSION majorversion) -ge 7 ]
logInfoNoEcho 4 "... $(basename "$0") done with autoRefresh='$autoRefresh'"
exit

