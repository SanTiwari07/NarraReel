# Installing ffmpeg

NarraReel calls `ffmpeg` to mix audio and render the video. Captions are burned in with **libass**, so the
build you install must include it. The H.264 encoder (`libx264`) is used for MP4 export, so check that too.

`narrareel doctor` tells you what is missing. This page has the exact commands for the common Linux
distributions, then shows how to check the result.

## Debian, Ubuntu and derivatives

```bash
sudo apt update
sudo apt install ffmpeg
```

## Fedora

Fedora's own `ffmpeg-free` package leaves out `libx264`, so MP4 export fails. Use the full build from
[RPM Fusion](https://rpmfusion.org/Configuration):

```bash
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf swap ffmpeg-free ffmpeg --allowerasing
```

## Arch Linux and Manjaro

The `ffmpeg` package in the official repositories includes libass and x264:

```bash
sudo pacman -S ffmpeg
```

## openSUSE

The ffmpeg in the default openSUSE repositories is built without some codecs. Use the
[Packman](https://en.opensuse.org/Additional_package_repositories#Packman) repository. This is the Tumbleweed
URL; for Leap replace `openSUSE_Tumbleweed` with `openSUSE_Leap_$releasever`:

```bash
sudo zypper addrepo -cfp 90 'https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Tumbleweed/Essentials' packman-essentials
sudo zypper refresh
sudo zypper install --from packman-essentials --allow-vendor-change ffmpeg
```

## Alpine Linux

```bash
sudo apk add ffmpeg        # as root, drop sudo
```

## NixOS (and Nix on any distro)

Use `ffmpeg-full`, which enables libass and x264. For a throwaway shell:

```bash
nix-shell -p ffmpeg-full
```

To install it for your user, run `nix profile install nixpkgs#ffmpeg-full`. On NixOS you can instead add it to
your configuration:

```nix
environment.systemPackages = [ pkgs.ffmpeg-full ];
```

## Check that it works

libass shows up as two filters, `ass` and `subtitles`. Both must be listed (a plain `grep ass` also matches
unrelated filters such as `allpass`, so match whole words):

```bash
ffmpeg -hide_banner -filters | grep -wE 'ass|subtitles'
```

Expected output (the flag columns differ a little between versions):

```text
 .. ass               V->V       Render ASS subtitles onto input video using the libass library.
 .. subtitles         V->V       Render text subtitles onto input video using the libass library.
```

Then check the H.264 encoder:

```bash
ffmpeg -hide_banner -encoders | grep libx264
```

Finally let NarraReel look for itself:

```bash
narrareel doctor
```

If the `libass (captions)` row says `available`, you are done.

## Using an ffmpeg that is not on your `PATH`

If you have a build elsewhere (for example a static build you downloaded), point NarraReel at it:

```bash
export NARRAREEL_FFMPEG=/opt/ffmpeg/bin/ffmpeg
```

If `ffprobe` is not on your `PATH`, NarraReel looks for it next to that file. Add the line to your shell profile to make it permanent.

## Still stuck?

Open an issue and paste the output of `narrareel doctor` and `ffmpeg -hide_banner -filters | grep -wE 'ass|subtitles'`.
