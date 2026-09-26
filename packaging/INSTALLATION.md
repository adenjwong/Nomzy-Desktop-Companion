# Installation and migration details

## Update and check your version

Quit Nomzy using the menu-bar paw → **Quit Nomzy** before updating. Extract the
new ZIP, drag `Nomzy.app` into `Applications`, and choose **Replace**. Launch the
copy in Applications. Open the menu-bar paw → **About Nomzy** to see the exact
running version (0.8.2 for this release).

Settings and saved position live outside the app at:

```text
~/Library/Application Support/Nomzy/Nomzy Desktop Companion/
```

Replacing or deleting the app leaves this folder intact. Back up this folder
before upgrading if you want a recoverable copy of your preferences. Quit Nomzy
before restoring a backup. Avoid running source and installed copies together.

## Move from a repository-run version

Recent source versions use the same user-data folder as the installed app, so
quit the source copy and launch the app from Applications; your preferences and
position carry over automatically.

Older versions saved `config/settings.json` and `config/state.json` inside the
repository. Before switching, back up those files, update the source checkout to
0.8.2 while preserving your customized config files, then run it once using the
[source instructions](../README.md#run-from-source) and quit. This migrates each file only when its
user-data counterpart is absent. Existing user data takes precedence. The
migration leaves the repository files untouched. Confirm your settings before
removing the checkout. The standalone app cannot discover an arbitrary old
repository and does not import its config automatically.

## Uninstall

1. Turn off **Launch at login** in Nomzy's Settings, then quit from the menu-bar
   paw. If the app is unavailable, remove/disable Nomzy in **System Settings →
   General → Login Items**.
2. Move `Applications/Nomzy.app` to Trash. Your preferences remain for reinstall.
3. Optionally, to remove preferences and saved position too, use Finder → Go →
   Go to Folder and enter `~/Library/Application Support/Nomzy/Nomzy Desktop Companion/`.
   Move that folder to Trash. This also removes data shared by source versions.
4. Optionally remove diagnostic logs at `~/Library/Logs/Nomzy/`.

If you keep an old source checkout, its `config` files can be imported again on a
future source launch. Keep a backup elsewhere or remove that checkout when you
want to remove all old user data. Removing the app alone does not delete it.

