#!/bin/bash
if [[ -n "$SYNOPKG_PKGNAME" ]]; then
  # $SYNOPKG_PKGNAME is available if pre-processing was well done! 
  LOG="/var/tmp/$SYNOPKG_PKGNAME.log"
else
  LOG="/var/tmp/UsbEject.log"
  echo "$(date "$DTFMT"): Error: SYNOPKG_PKGNAME is not set in install_uifile.sh !!!???" >> "$LOG"
fi  
DTFMT="+%Y-%m-%d %H:%M:%S"
SCRIPTPATHTHIS="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
user=$(whoami)
scriptpathParent=${SCRIPTPATHTHIS%/*}
echo "$(date "$DTFMT"): Start of $0 to put values from config file (if available) to '$SYNOPKG_TEMP_LOGFILE', which replaces install_uifile (as $user)" >> "$LOG"

if [[ -n "$SYNOPKG_DSM_LANGUAGE" ]]; then
  lng="$SYNOPKG_DSM_LANGUAGE" # lng of actual user
  echo "$(date "$DTFMT"): from environment SYNOPKG_DSM_LANGUAGE: '$lng'" | tee -a "$LOG"
else
  declare -A ISO2SYNO
  ISO2SYNO=( ["de"]="ger" ["en"]="enu" ["zh"]="chs" ["cs"]="csy" ["jp"]="jpn" ["ko"]="krn" ["da"]="dan" ["fr"]="fre" ["it"]="ita" ["nl"]="nld" ["no"]="nor" ["pl"]="plk" ["ru"]="rus" ["sp"]="spn" ["sv"]="sve" ["hu"]="hun" ["tr"]="trk" ["pt"]="ptg" )
  if [[ -n "${LANG}" ]]; then
    env_lng="${LANG:0:2}"
    lng=${ISO2SYNO[$env_lng]}
  fi  
fi
if [[ -z "$lng" ]] || [[ "$lng" == "def" ]]; then
  lng="enu"
  echo "$(date "$DTFMT"): No language in environment found, using 'enu'" >> "$LOG"
fi

JSON="$(dirname "$0")/wizard_$lng.json"
if [[ ! -f "$JSON" ]]; then # no translation to the actual language available
  JSON=$(dirname "$0")/wizard_enu.json # using English version
fi  
if [ ! -f "$JSON" ]; then
  echo "$(date "$DTFMT"): ERROR 11: WIZARD template file '$JSON' not available!" | tee -a "$LOG"
  echo "[]" >> "$SYNOPKG_TEMP_LOGFILE"
  echo "$(date "$DTFMT"): No upgrade_uifile ($$SYNOPKG_TEMP_LOGFILE) generated (only empty file)" >> "$LOG"
  exit 11 # should we use exit 0 ?
fi
echo "$(date "$DTFMT"): WIZARD template file '$JSON' is available" >> "$LOG"
# after uninstall is /var/packages/$SYNOPKG_PKGNAME no more available, only /volume1/@appdata/UsbEject/config !!!
#configFilePathName="/var/packages/$SYNOPKG_PKGNAME/var/config"
configFilePathName="${SCRIPTPATHTHIS%%/@*}/@appdata/${SYNOPKG_PKGNAME}/config"
if [ ! -f "$configFilePathName" ]; then
  echo "$(date "$DTFMT"): File '$configFilePathName' not found" | tee -a "$LOG"
  configFilePathName="${SCRIPTPATHTHIS%%/@*}/@appdata/${SYNOPKG_PKGNAME}/config"  # version <1.10 used config in this folder  
fi
if [ ! -f "$configFilePathName" ]; then
  echo "$(date "$DTFMT"): No Cfg-File not found, using initial config" | tee -a "$LOG"
  configFilePathName="$(dirname "$0")/initial_config.txt"
fi
echo "$(date "$DTFMT"): Used config file: '$configFilePathName'" >> "$LOG"

cat "$JSON" >> "$SYNOPKG_TEMP_LOGFILE"
fields="WAIT BEEP LED_COPY EJECT_TIMEOUT LOG_MAX_LINES NOTIFY_USERS LOGLEVEL HDPARM_SPINDOWN"
msg=""
for f1 in $fields; do
  line=$(grep "^$f1=" "$configFilePathName")
  if [[ -z "$line" ]]; then # new item in this version
    line=$(grep "^$f1=" "$(dirname "$0")/initial_config.txt")  
  fi
  eval "$line"
  sed -i -e "s|@${f1}@|${!f1}|g" "$SYNOPKG_TEMP_LOGFILE" # replace placeholder by value in upgrade_uifile
  msg="$msg, $f1='${!f1}'"
done
echo "$(date "$DTFMT"): Found settings: $msg" >> "$LOG"      

echo "$(date "$DTFMT"): Wizzard template copied to '$SYNOPKG_TEMP_LOGFILE' and values from config inserted" >> "$LOG"
echo "$(date "$DTFMT"): ... $0 done" >> "$LOG"
exit 0
# next steps will be: start-stop prestop, start-stop stop of old package if it's an upgrade
#                     preupgrade (optional)
#                     preuninst and postuninst from old package if it's an upgrade
#                     prereplace ??
#                     preinst

