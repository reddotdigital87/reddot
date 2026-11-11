import {Composition} from 'remotion';
import config from '../../reel/reel_config.json';
import {BeastReel, reelDuration, ReelConfig} from './BeastReel';

const reel = config as unknown as ReelConfig;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="BeastReel"
    component={BeastReel}
    width={1080}
    height={1920}
    fps={reel.fps}
    durationInFrames={reelDuration(reel)}
    defaultProps={reel}
    calculateMetadata={({props}) => ({durationInFrames: reelDuration(props)})}
  />
);
