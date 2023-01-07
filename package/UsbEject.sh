#!/bin/bash
# called from udev. Attention: Environment (e.g. PATH) is not set!
# Horst Schmid 2023-01

# shellcheck disable=SC1090 # https://www.shellcheck.net/ (warning): ShellCheck can't follow non-constant source.

# How to run long time process on Udev event?
# https://unix.stackexchange.com/questions/56243/how-to-run-long-time-process-on-udev-event

# default settings
TRIES=20
WAIT=0 # wait (seconds) time after mountpoint found

# $1 is e.g. 'usb1p1', $2 empty if started from udev daemon, S2="START" if started from start-stop-status script

# if the last line in "$SCRIPT_EXEC_LOG" contains $1, then replace that line by $2, else append $2
# This is to reduce the number of entries in $SCRIPT_EXEC_LOG
replaceLastLogLineIfSimilar() {
  latestEntry="$(/bin/tail -1 "$SCRIPT_EXEC_LOG")"
  if [[ "$latestEntry" == *"$1"* ]]; then
    lineCount=$(/bin/wc -l < "$SCRIPT_EXEC_LOG")
    /bin/sed -i -e "$lineCount,\$d" "$SCRIPT_EXEC_LOG"
    /bin/echo "$(date "$DTFMT"): $2" >> "$SCRIPT_EXEC_LOG"
    logInfo 8 "Last Entry in SCRIPT_EXEC_LOG replaced"
  else
    logInfo 8 "Item '$1' not found in SCRIPT_EXEC_LOG last line: '$latestEntry'"
  fi # if [[ "$latestEntry" == *"$diskName"* ]]
}



######################### start point #####################
# environment PATH is empty when started via event!!!

SCRIPTPATHTHIS="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )" # e.g. /volumeX/@appstore/<app>
if [[ -z "$SYNOPKG_PKGNAME" ]]; then
  SYNOPKG_PKGNAME=${SCRIPTPATHTHIS##*/}
  myMsg="SYNOPKG_PKGNAME='$SYNOPKG_PKGNAME' extracted from SCRIPTPATHTHIS"
else
  myMsg="SYNOPKG_PKGNAME='$SYNOPKG_PKGNAME' was available"
fi
# source "/var/packages/$SYNOPKG_PKGNAME/var/config" # import our config: done inside of common!

# import helper functions logInfo(), beepError() and beep() (also used for LED control):
if [[ ! -x "/var/packages/$SYNOPKG_PKGNAME/target/common" ]]; then
  /bin/echo "###########################################################################"
  /bin/echo "Error: File '/var/packages/$SYNOPKG_PKGNAME/target/common' not available or not executable!" | tail -a "/var/log/packages/$SYNOPKG_PKGNAME.log"
  /bin/echo "###########################################################################"
  exit 1
fi
source "/var/packages/$SYNOPKG_PKGNAME/target/common" "$SYNOPKG_PKGNAME" # lngUser, lngMail (for Logfile) set, $APPDATA/config read
dsmappname=""
eval "$(grep "dsmappname=" "/var/packages/$SYNOPKG_PKGNAME/INFO")" # set via file INFO, e.g. ""SYNO.SDS._ThirdParty.App.UsbEject""
/bin/echo -e "" >> "$LOGFILE" # empty row
user=$(whoami) # EnvVar $USER may be not well set
versShell="$($SHELL --version | sed -n '1p')"
logInfo 3 "Start of $0 as user '$user' with SHELL='$SHELL' ($versShell) ..."
logInfo 6 "$myMsg"
cmd="$(/bin/cat /proc/$PPID/comm)"
logInfo 8 "$(basename "$0"), P1='$1', P2='$2', BASHPID='$BASHPID', PID='$$', Parent is $PPID: $cmd" >> "$LOG"
# in a sub shell (with $BASH_SUBSHELL==1) the BASHPID is different from $$
if [ -z "$1" ]; then
  /bin/echo "incorrect '\$1' - aborting ..."
  logInfo 0 "Error: Parameter 1 missing in $0"
  beepError
  exit 1
fi

MOUNTPATH="" # external Disk
eval "$(grep "dsmappname=" "/var/packages/$SYNOPKG_PKGNAME/INFO")"
logInfo 6 "The 'dsmappname', the class for synodsmnotify is '$dsmappname'"
# dsmappname needs to match the .url in ui/config. Otherwise synodsmnotify will not work
# used as CLASS in synodsmnotify
COUNT=0
SCRIPT_EXEC_LOG="$APPDATA/execLog" # logfile with 1 ..2 lines per inserted and ejected USD storage drive
if [[ -f "$SCRIPT_EXEC_LOG" ]]; then
  logInfo 6 "File $SCRIPT_EXEC_LOG exists"
  lineCount=$(/bin/wc -l < "$SCRIPT_EXEC_LOG")
  logInfo 6 "The log file '$SCRIPT_EXEC_LOG' has $lineCount lines, configured maximum is $LOG_MAX_LINES"
  # /bin/echo "lineCount=$lineCount"
  if [[ "$lineCount" -gt "$LOG_MAX_LINES" ]]; then
    newLineCount=$((LOG_MAX_LINES / 2))
    delLines=$((lineCount - newLineCount))
    /bin/sed -i -e "1,${delLines}d" "$SCRIPT_EXEC_LOG"
    logInfo 4 "The log file '$SCRIPT_EXEC_LOG' was trimmed from $lineCount to $newLineCount lines"
  fi
else
  /bin/touch "$SCRIPT_EXEC_LOG" # created an empty file
  /bin/chown "$SYNOPKG_PKGNAME":"$SYNOPKG_PKGNAME" "$SCRIPT_EXEC_LOG" # make it accessable & readable for the cgi scripts
  /bin/chmod 644 "$SCRIPT_EXEC_LOG"
fi

if [[ -f "$LOG" ]]; then
  lineCount=$(/bin/wc -l < "$LOG")
  logInfo 6 "The log file '$LOG' has $lineCount lines, configured maximum is $LOG_MAX_LINES"
  if [[ $lineCount -gt "$LOG_MAX_LINES" ]]; then
    newLineCount=$((LOG_MAX_LINES / 2))
    delLines=$((lineCount - newLineCount))
    /bin/sed -i -e "1,${delLines}d" "$LOG"
    logInfo 4 "The log file '$LOG' was trimmed from $lineCount to $newLineCount lines"
  fi
else
  /bin/touch "$LOG"
  /bin/chown "$SYNOPKG_PKGNAME":"$SYNOPKG_PKGNAME" "$LOG"
  /bin/chmod 644 "$LOG"
fi

# try to get the mount path
logInfo 5 "device '$1' - inserted, trying to find mount point"
COUNT=0
# WAIT statt TRIES verwenden!!!!
while [ -z "$MOUNTPATH" ] && [ $COUNT -lt $TRIES ] ; do
  MOUNTPATH=$(/bin/mount 2>&1 | /bin/grep "/dev/$1" | /bin/cut -d ' ' -f3)
  if [ -z "$MOUNTPATH" ]; then
    COUNT=$((COUNT+1))
    /bin/sleep 1s
  fi
done

# abort when nothing is found
if [ -z "$MOUNTPATH" ]; then
  logInfo 0 "device '$1' - unable to find mount point within $COUNT seconds, aborting"
  beepError
  exit 1
fi
logInfo 3 "device '$1' - mount point '$MOUNTPATH' found after $COUNT seconds"

dateMount_s=$(date +"%s")
dateMount_string=$(date "$DTFMT")
if (((LED_COPY & 1)!=0)); then
  beep LED_COPY_ON
elif (((LED_COPY & 2)!=0)); then
  beep LED_COPY_FLASH
fi

# sleep some time because Synology does some crazy stuff like un- and remounting on SATA
/bin/sleep $WAIT
usbNo=${MOUNTPATH%/*} # remove /usbshare from e.g. /volumeUSB2/usbshare
usbNo=${usbNo#*volumeUSB}
# /bin/echo "usbNo=$usbNo"
diskID1=$(/bin/grep "${usbNo}=" "/usr/syno/etc/usbno_guid.map") # e.g. 14="20190123456780"
diskID2=${diskID1%0\"}  # remove trailing '0"'
diskID2=${diskID2#*=\"} # Remove leading Quote, now e.g. "2019012345678"
# /bin/echo "diskID=$diskID"
diskName=$(/usr/syno/bin/lsusb | /bin/grep "$diskID2") # e.g. "|__2-2.2 1234:5678:90AB 00 3.00 5000MBit/s 8mA 1IF (...)"
 # lsusb -cI
diskPort="${diskName#*|__}"
diskPort="${diskPort%% *}" # e.g. 2-2.2
diskName=${diskName#*(}
diskName=${diskName%)*}
# /bin/echo "diskName=$diskName" # e.g. "Intenso external USB 3.0 2019012345678"
if [[ "$2" != "START" ]]; then
  /bin/echo "$(date "$DTFMT"): Disk '$diskName' mounted as $MOUNTPATH ..." >> "$SCRIPT_EXEC_LOG"
fi
# /volumeX/@appdata/UsbEject = /var/packages/UsbEject/var/
# device with MOUNTPATH "/volumeUSB12/usbshare/" is shown as "usbshare12" in File Station
path="${MOUNTPATH##*/}${usbNo}" # e.g. "usbshare12"
echo "$path:${MOUNTPATH}:$diskName:$diskPort" > "/var/packages/UsbEject/tmp/$1" # generate marker-File
            # e.g. items[0]="usbshare12", items[1]="/volumeUSB12/usbshare/", items[2]="Seagate Expansion HDD 00000000NXZ000N"
chmod 666 "/var/packages/UsbEject/tmp/$1"
chown "$SYNOPKG_PKGNAME:$SYNOPKG_PKGNAME" "/var/packages/UsbEject/tmp/$1"
logInfo 3 "UsbEject.sh, waiting endless till MOUNTPATH gets invalid or /var/packages/UsbEject/tmp/$1 is no more available ..."
while [[ -f "/var/packages/UsbEject/tmp/$1" ]] && [[ -d "$MOUNTPATH" ]]; do # file not deleted and not ejected in another way
  sleep 0.5
done
if [[ ! -f "/var/packages/UsbEject/tmp/$1" ]]; then
  # file was most probably renamed by index.cgi from ${1} to ${1}__<UserName>
  f1="$(basename "$(ls -A "/var/packages/UsbEject/tmp/${1}__"* )")"
  userName="${f1##*__}"
  logInfo 3 "UsbEject.sh, file '$f1', UserName is '$userName' (or 'STOP')"
  if [[ "$userName" == "STOP" ]]; then # File was renamed by start-stop-status script
    logInfo 3 "UsbEject.sh, STOP-File $f1 found: Exit from $0 for $1 without ejecting"
    rm "/var/packages/UsbEject/tmp/$f1"
    exit 1
  fi
  logInfo 3 "UsbEject.sh, $MOUNTPATH was requested to ejected now by user '${userName}' ..."
  #echo "$path:${MOUNTPATH}:$diskName" > "/var/packages/UsbEject/tmp/$1_ejecting" # generate new marker-File
  mv "$f1" "/var/packages/UsbEject/tmp/$1_ejecting"
fi

ejected=0 # 0: no eject, 1: ejecting, 2: eject success, 3: eject fail
FREE="" # if mountpath is no more available, we can't get free space
if [[ -d "$MOUNTPATH" ]]; then # not ejected in another way
  FREE=$(/bin/df -h "$MOUNTPATH" | /bin/grep "$MOUNTPATH" | /bin/awk '{ print $4 }')  # e.g. "2.1T"
  logInfo 2 "UsbEject.sh, device '$1' needs to be ejected now ..."
  if [[ -n "$HDPARM_SPINDOWN" ]] && [[ "$HDPARM_SPINDOWN" =~ ^[0-9]+$ ]]; then # Attention: No single or double quotes for regExp allowed!
    d1=$(/bin/echo "/dev/$1" | /bin/sed 's:p.*::') # d1 is now e.g. '/dev/usb1'
    result=$(/bin/hdparm -S "$HDPARM_SPINDOWN" "$d1") # SpinDown after 15 minutes of idle time
    logInfo 3 "hdparm -S $HDPARM_SPINDOWN $d1 result: '$result'"
  fi
  d1=$(/bin/echo "$1" | /bin/sed 's:/dev/::' | /bin/sed 's:p.*::') # # $1 is e.g. 'usb1p1' or '/dev/usb1p1', d1 is now e.g. 'usb1'
  info=$(/usr/syno/bin/synousbdisk -info "$d1")
  sn=$(/bin/echo "$info" | /bin/grep "Share Name:") # catch line with the share name
  sn=${sn#*:} # remove the label
  sn=$(/bin/echo "$sn") # remove blanks, so we get e.g. usbshare4
  ejected=1  #1: ejecting, 2: eject success, 3: eject fail
  endTime=$(($(date +%s) + EJECT_TIMEOUT))
  k=$TRIES # $TRIES is from the config file
  while [[ $(date +%s) -le $endTime ]]; do # loop with counter as the external drive may be in use ...
    ((k--))
    # try to do the unmount
    logInfo 8 "UsbEject.sh, till eject timeout left $(( endTime - $(date +%s) ))"
    # /bin/sleep 3
    /bin/sync
    /bin/sleep 2
    /usr/syno/bin/synousbdisk -rcclean
    /bin/sleep 2

    # /bin/umount $MOUNTPATH
    resultd=$(/usr/syno/bin/synousbdisk -umount "$d1")
    retvald=$?
    if [ $retvald -eq 0 ];then # success
      # 2nd Part of umount (neccessary?)
      results=$(/usr/syno/bin/synousbdisk -umount "$sn")
      retvals=$?
    fi
    # sleep 45
    logInfo 7 "UsbEject.sh, Loop $((TRIES-k)): synousbdisk -umount $d1 was $retvald ($resultd), synousbdisk -umount $sn was $retvals ($results)"
    # check whether now realy no more mounted:
    resultm=$(/bin/mount 2>&1 | /bin/grep "/dev/$1" | /bin/cut -d ' ' -f3)
    if [ -z "$resultm" ]; then # synousbdisk -umount was really successfull
      logInfo 5 "UsbEject.sh, Updating now /tmp/usbtab ..."
      ejected=2 # 0: no eject, 1: ejecting, 2: eject success, 3: eject fail
      # Remove it now from the 'gui' list:
      cp /tmp/usbtab /tmp/usbtab.old
      /bin/grep -v "$d1" /tmp/usbtab.old > /tmp/usbtab  # copy all non-matching lines
      rm -f /tmp/usbtab.old
      # unbind ??? # Optional !!!????
      logInfo 3 "UsbEject.sh, device '$1' successfully unmounted and removed from GUI!"
      break
    fi
    if [[ $ejected -eq 1 ]]; then
      logInfo 4 "UsbEject.sh, Drive seems busy! k=$k Please wait ..."
      sleep 5
    fi
  done # while not timeout
  if [[ $ejected -eq 1 ]]; then
    /bin/echo "$(date "$DTFMT"): Attention: The disk '$diskName', mounted as $MOUNTPATH, was tried to eject, but that failed!!" >> "$SCRIPT_EXEC_LOG"
    ejected=3 # failed
  fi
  logInfo 4 "UsbEject.sh, Eject part finished with $ejected. (2: eject success, 3: eject fail) "
  if [[ $ejected -eq 3 ]]; then
    # Ejection of device failed!
    if [[ -n "$NOTIFY_USERS" ]]; then
      /usr/syno/bin/synodsmnotify -c "$dsmappname" "$NOTIFY_USERS" "$SYNOPKG_PKGNAME:app1:title01" "$SYNOPKG_PKGNAME:app1:msg1" "$MOUNTPATH"
    fi
    /bin/echo "$(date "$DTFMT"): Ejection of '$diskName', mounted as $MOUNTPATH failed! The timeout for this is configured to $EJECT_TIMEOUT seconds." >> "$SCRIPT_EXEC_LOG"
  else
    if [[ -n "$NOTIFY_USERS" ]]; then
      /usr/syno/bin/synodsmnotify -c "$dsmappname" "$NOTIFY_USERS" "$SYNOPKG_PKGNAME:app1:title01" "$SYNOPKG_PKGNAME:app1:msg2" "$MOUNTPATH" "$FREE"
    fi
  fi
else
  logInfo 3 "UsbEject.sh, /var/packages/UsbEject/tmp/$1 is still available but mountpath no more. Ejected in another way!"
fi
dateEject_s=$(date +"%s")

if (((LED_COPY & 7)!=0)); then
  beep LED_COPY_OFF # Copy LED off
  if [[ "$ejected" -eq "3" ]]; then
    #  if (((LED_COPY & 4)!=0)); then
    beep LED_COPY_FLASH
    #  fi
  fi
fi # if LED_COPY

mountDuration_s=$(( dateEject_s - dateMount_s ))
if ((mountDuration_s > 60 )); then
  (( execTime_min = mountDuration_s / 60 ))
  (( mountDuration_s = mountDuration_s % 60 ))
  mountDuration="${mountDuration_s}s"
  if ((execTime_min > 60 )); then
    (( execTime_h = execTime_min / 60 ))
    (( execTime_min = execTime_min % 60 ))
    mountDuration="${execTime_h}h ${execTime_min}min $mountDuration"
  else
    mountDuration="${execTime_min}min $mountDuration"
  fi
else
  mountDuration="$mountDuration_s seconds"
fi
if [[ "$ejected" -ne "3" ]]; then
  rm -f "/var/packages/UsbEject/tmp/$1"* # delete marker file
  logInfo 4 "UsbEject.sh, Eject done with ${ejected}. Marker file deleted!"
else
  logInfo 4 "UsbEject.sh, Eject failed with ${ejected}. Marker file not deleted!"
fi

if [[ "$ejected" -eq "0" ]] || [[ "$ejected" -eq "2" ]]; then   # 0: no eject, 1: ejecting, 2: eject success, 3: eject fail
  # if the last line in "$SCRIPT_EXEC_LOG" contains $1, then replace that line by $2, else append $2
  # This is to reduce the number of entries in $SCRIPT_EXEC_LOG
  replaceLastLogLineIfSimilar "Disk '$diskName' mounted as $MOUNTPATH" "The disk '$diskName', mounted as $MOUNTPATH, was mounted $dateMount_string and ejected after $mountDuration by ${userName}. ${FREE}Bytes free"
fi
exit 0

