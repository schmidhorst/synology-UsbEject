#!/bin/bash
LOG="/var/tmp/$SYNOPKG_PKGNAME.log"
DTFMT="+%Y-%m-%d %H:%M:%S"
user=$(whoami)
echo "$(date "$DTFMT"): Start of $0 to put values from wizard_enu.json and the config file to $SYNOPKG_TEMP_LOGFILE, which replaces upgrade_uifile (as $user)" >> "$LOG"

if [[ -n "$SYNOPKG_DSM_LANGUAGE" ]]; then
  lng="$SYNOPKG_DSM_LANGUAGE" # lng of actual user
  echo "$(date "$DTFMT"): from environment SYNOPKG_DSM_LANGUAGE: '$lng'" | tee -a "$LOG" # normally available, lng of actual user
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
echo "$(date "$DTFMT"): WIZARD template file '$JSON' available" >> "$LOG"
configFilePathName="/var/packages/$SYNOPKG_PKGNAME/var/config"
if [ ! -f "$configFilePathName" ]; then
  echo "$(date "$DTFMT"): Suspicious: Upgrade, but no old configuration available!" | tee -a "$LOG"
  # echo "[]" >> "$SYNOPKG_TEMP_LOGFILE"
  # echo "$(date "$DTFMT"): No upgrade_uifile ($$SYNOPKG_TEMP_LOGFILE) generated (only empty file)" >> "$LOG"
  # exit 0
  echo "$(date "$DTFMT"): No Cfg-File not found, using initial config" | tee -a "$LOG"
  configFilePathName="$(dirname "$0")/initial_config.txt"
else
  echo "$(date "$DTFMT"): Used config file: '$configFilePathName'" >> "$LOG"
fi

cat "$JSON" >> "$SYNOPKG_TEMP_LOGFILE"
fields="WAIT BEEP LED_COPY EJECT_TIMEOUT LOG_MAX_LINES NOTIFY_USERS LOGLEVEL HDPARM_SPINDOWN"
msg=""
for f1 in $fields; do
  line=$(grep "^$f1=" "$configFilePathName")
  if [[ -z "$line" ]]; then # new item in this version
    line=$(grep "^$f1=" "$(dirname "$0")/initial_config.txt")  
    echo "$(date "$DTFMT"): Item '$f1' line from initial_config.txt: '$line' " >> "$LOG"
    eval "$line"
    msg="$msg, $f1='${!f1}' (initial value)"
  else
    eval "$line"
    msg="$msg, $f1='${!f1}' (previously configured)"    
  fi
  sed -i -e "s|@${f1}@|${!f1}|g" "$SYNOPKG_TEMP_LOGFILE" # replace placeholder by value in upgrade_uifile
done
echo "$(date "$DTFMT"): Found settings: $msg" >> "$LOG"      

echo "$(date "$DTFMT"): Values from '$JSON' and '$configFilePathName' put to template '$SYNOPKG_TEMP_LOGFILE'" >> "$LOG"
echo "$(date "$DTFMT"): ... $0 done" >> "$LOG"
# putting here somthing to ENV for use in postinst script is not working!
exit 0

