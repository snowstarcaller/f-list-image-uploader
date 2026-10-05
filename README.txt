F-LIST IMAGE UPLOADER
=====================

Uploads a whole folder of pictures to an F-list character for you, one at a
time, doing the "Choose file" then "Add Image" clicks automatically.

You log in to F-list yourself in a normal browser window. The program never
sees or stores your password.


ONE-TIME SETUP
--------------
1. Install Python (free) from https://www.python.org/downloads/
   - Windows: on the first installer screen, TICK "Add python.exe to PATH".
   - Mac: run the installer from python.org (don't rely on the built-in one).
2. Unzip this folder somewhere handy, e.g. your Desktop.

That's it. The first time you start it, it sets itself up, which takes a
minute or two. You need Google Chrome or Microsoft Edge installed (Windows
always has Edge); if neither is there it downloads a browser on its own.


USING IT
--------
1. Start it:
   - Windows: double-click  "Start (Windows).bat"
     (If Windows shows "Windows protected your PC", click More info, then Run anyway.)
   - Mac: right-click "Start (Mac).command" and choose Open, then Open again.
     (Right-click is only needed the first time.)
2. In the small window that appears:
   - Click Browse... and pick the folder with your pictures.
   - Choose "Upload all of them" or "Upload only the first [N] pictures".
   - Click Go.
3. A browser window opens on F-list. In it:
   - Log in (only needed the first time, it remembers you after that).
   - Go to your character, click Edit, and open the Images section so you can
     see the "Add a new image" box and the "Add Image" button.
4. Back in the uploader window, click Continue.
5. Sit back. Each picture is uploaded in turn and the log shows progress.
   Click Stop at any time to stop after the current picture.
6. When it says Finished, check your profile in the browser, then click
   Continue to close the browser.


GOOD TO KNOW
------------
- Pictures go up in filename order (pic2 comes before pic10). Rename them
  with numbers if you want a particular order; you can also drag to reorder
  on F-list afterwards.
- F-list's rules are checked before anything is sent. Files that would be
  refused are skipped and listed in the log:
    * only png, jpg and gif
    * under 2.0 MB
    * under 4000 pixels wide and tall
- F-list allows 50 images per character. If your character already has
  some, the uploader warns you, and it stops by itself if two uploads in a
  row fail (which is usually the limit being reached).
- If your character page might need a Save after adding images, click it
  in the browser before closing.


IF SOMETHING GOES WRONG
-----------------------
- "Couldn't find the 'Add Image' button": make sure the browser is on your
  character's EDIT page with the Images section opened, then press Continue.
- Nothing happens when double-clicking on Windows: Python probably isn't on
  PATH. Reinstall Python and tick "Add python.exe to PATH".
- To start completely fresh (e.g. to log in as someone else), delete the
  ".flist-uploader-browser" folder in your home folder and the ".venv"
  folder inside this folder.


FOR THE TECHNICALLY MINDED
--------------------------
There is also a command-line mode:
    python flist_uploader.py "C:\path\to\pictures" --count 20
It needs:  pip install playwright pillow
