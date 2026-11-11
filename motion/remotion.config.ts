import {Config} from '@remotion/cli/config';
import fs from 'node:fs';

// Use the preinstalled headless Chromium when present (cloud sessions);
// otherwise Remotion downloads its own browser.
const localShell =
  '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell';
if (fs.existsSync(localShell)) {
  Config.setBrowserExecutable(localShell);
}

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setConcurrency(4);
