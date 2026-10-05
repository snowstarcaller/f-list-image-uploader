# F-list Image Uploader

Uploads a whole folder of pictures to your F-list character for you. Instead of clicking **Choose file** and **Add Image** over and over, you pick a folder, press **Go**, and it does the clicking one picture at a time while you watch.

- Works on **Windows** and **Mac**.
- You log in to F-list yourself in a normal browser window. **The program never sees or stores your password.**
- It's free. No account or sign-up is needed beyond your own F-list login.

---

## ⬇️ Download

**[Click here to download the latest version (flist-uploader.zip)](../../releases/latest)**

On that page, click **flist-uploader.zip** under "Assets" to download it.

> If that link doesn't work, click the green **Code** button near the top of this page, then **Download ZIP**.

---

## Step 1: Install Python (one time only)

The uploader needs a free program called Python. You only do this once.

### On Windows
1. Go to **https://www.python.org/downloads/** and click the big yellow **Download Python** button.
2. Open the file you downloaded.
3. ⚠️ **Important:** on the very first installer screen, tick the box at the bottom that says **"Add python.exe to PATH"**.
4. Click **Install Now** and wait for it to finish, then close the installer.

### On Mac
1. Go to **https://www.python.org/downloads/** and click the big yellow **Download Python** button.
2. Open the file you downloaded and click through the installer (Continue, Agree, Install).
3. Use the installer from python.org even if your Mac says it already has Python.

You also need **Google Chrome** or **Microsoft Edge** on your computer. Windows always has Edge, so most people already have this covered. If neither is found, the uploader downloads a browser by itself.

---

## Step 2: Unzip the download (one time only)

1. Find **flist-uploader.zip** in your Downloads folder.
2. **Windows:** right-click it and choose **Extract All...**, then **Extract**.
   **Mac:** double-click it.
3. You'll get a folder called **flist-uploader**. Move it somewhere easy to find, like your Desktop.

⚠️ On Windows, don't run it from *inside* the zip. Always extract it first.

---

## Step 3: Start the uploader

Open the **flist-uploader** folder.

### On Windows
Double-click **`Start (Windows).bat`**.

- If a blue box says **"Windows protected your PC"**, click **More info**, then **Run anyway**. This appears because the file is new to Windows, not because anything is wrong.

### On Mac
**Right-click** (or Control-click) **`Start (Mac).command`** and choose **Open**, then click **Open** again in the box that appears.

- You only need to right-click the first time. After that, a normal double-click works.

**The very first time** you start it, a black window appears and sets things up. This takes a minute or two. Leave it open. Every time after that, it starts in a few seconds.

---

## Step 4: Upload your pictures

1. A small window called **F-list Image Uploader** appears.
2. Click **Browse...** and choose the folder that has your pictures in it.
3. Choose how many to upload:
   - **Upload all of them**, or
   - **Upload only the first [number]** pictures, and type a number.
4. Click **Go**.
5. A browser window opens on F-list. In that browser window:
   - **Log in** to F-list. (Only needed the first time; it remembers you after that.)
   - Go to your **character**, click **Edit**, and open the **Images** section, so you can see the **"Add Image"** button.
6. Go back to the small uploader window and click **Continue**.
7. Sit back. Each picture is uploaded one by one, and the window shows the progress. Click **Stop** at any time to stop after the current picture.
8. When it says **Finished**, look at your character in the browser to check everything is there. If F-list shows a **Save** button, click it. Then click **Continue** in the uploader to close the browser.

That's it! 🎉

---

## Good to know

- **Order:** pictures go up in filename order (and it's smart about numbers, so `pic2` comes before `pic10`). If you want a certain order, rename the files with numbers first. You can also drag them into a new order on F-list afterwards.
- **F-list's rules are checked first.** Any picture F-list would refuse is skipped and listed in the window, so nothing gets stuck. F-list only accepts:
  - **PNG, JPG or GIF** files
  - **under 2 MB** in size
  - **under 4000 pixels** wide and tall
- **50 picture limit:** F-list allows 50 images per character. If your character already has some, the uploader warns you, and it stops on its own if two uploads in a row fail (that usually means the limit was reached).

---

## Help! Something went wrong

**Double-clicking the Windows file does nothing, or a window flashes and closes**
Python probably isn't set up correctly. Run the Python installer again, and this time make sure you tick **"Add python.exe to PATH"** on the first screen.

**It says "Python isn't installed"**
Do Step 1 again, then try once more.

**It says "Couldn't find the 'Add Image' button"**
Make sure the browser window is showing your character's **Edit** page with the **Images** section open (you should see the "Add Image" button). Then click **Continue** again.

**Mac says the file "can't be opened because it is from an unidentified developer"**
Right-click the file and choose **Open** instead of double-clicking (see Step 3).

**I want to log in as a different person, or start completely fresh**
Close the uploader. Then delete these two folders:
- the **`.flist-uploader-browser`** folder in your home folder
- the **`.venv`** folder inside the flist-uploader folder

These folders are hidden. On Windows, in File Explorer click **View**, then **Show**, then **Hidden items**. On Mac, press **Cmd + Shift + .** (full stop) in Finder.

**Still stuck?** Take a screenshot of the uploader window and send it to whoever shared this with you.

---

## Is this safe?

- You type your password into the real F-list website in a normal browser window. The uploader never sees it.
- The uploader only clicks the same buttons you would click yourself.
- All the code is right here on this page for anyone to read: [`flist_uploader.py`](flist_uploader.py).

---

## For the technically minded

There's also a command-line mode:

```
pip install playwright pillow
python flist_uploader.py "C:\path\to\pictures" --count 20
```

Run `python flist_uploader.py --help` for all options. The Start files simply create a `.venv`, install `playwright` and `pillow` into it, and launch the window.
