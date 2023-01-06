# Synology USB Storage Eject for Non-Admin Users
By default Synology allows only users with administration rights to securely eject USB storage devices. Users without administrator permissions don't have any eject buttons or eject menu items. To unplug such devices without having them previously unmounted, may lead to corrupted data of corrupted file system and produces a warning on the DSM system.
This package allows userers without administration rights to safely eject USB devices:
![user view](https://github.com/schmidhorst/synology-UsbEject/blob/main/ScreenshotUser.png?raw=true)
The administrator view gives more info and allows to set a filter:
![user view](https://github.com/schmidhorst/synology-UsbEject/blob/main/ScreenshotAdmin.png?raw=true)

## [License](https://htmlpreview.github.io/?https://github.com/schmidhorst/synology-UsbEject/blob/main/package/ui/licence_enu.html)

## Disclaimer and Issue Tracker
You are using everything here at your own risk.
For issues please use the [issue tracker](https://github.com/schmidhorst/synology-UsbEject/issues) with German or English language

# Installation
* Download the *.spk file from ["Releases"](https://github.com/schmidhorst/synology-UsbEject/releases), "Assets" to your computer and use "Manual Install" in the Package Center.

Third Party packages are restricted by Synology in DSM 7. Since autorun does require root
permission to perform its job an additional manual step is required after the installation.

SSH to your NAS (as an admin user) and execute the following command:
```shell
sudo cp /var/packages/UsbEject/conf/privilege.root /var/packages/UsbEject/conf/privilege
```
Alternative to SSH:
Go to Control Panel => Task Scheduler => Create => Scheduled Task => User-defined Script. In the "General" tab set any task name, select 'root' as user. In the "Task Settings" tab enter
```shell
cp /var/packages/UsbEject/conf/privilege.root /var/packages/UsbEject/conf/privilege
```
as "Run command". Finish it with OK. When you are requested to execute that command now during package installation, then go to the task scheduler, select that task and "Run" it.
## Credits and References
- This package was developed as a modification of [Synology Autorun](https://github.com/schmidhorst/synology-autorun/)
