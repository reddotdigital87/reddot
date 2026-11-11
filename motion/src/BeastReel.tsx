import {
  AbsoluteFill,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {slide} from '@remotion/transitions/slide';
import {noise2D} from '@remotion/noise';

export type Scene = {
  duration: number;
  kicker?: string;
  lines: string[];
  cta?: boolean;
};

export type ReelConfig = {
  brand: string;
  handle: string;
  keyword: string;
  fps: number;
  colors: {bg_top: string; bg_bottom: string; accent: string; text: string; muted: string};
  scenes: Scene[];
};

const TRANSITION = 12; // frames each scene overlaps the next

export const reelDuration = (cfg: ReelConfig) =>
  Math.round(cfg.scenes.reduce((sum, s) => sum + s.duration, 0) * cfg.fps);

const fontFaces = `
@font-face {font-family: 'Inter'; font-weight: 500; src: url('${staticFile('fonts/Inter-Medium.otf')}');}
@font-face {font-family: 'Inter'; font-weight: 700; src: url('${staticFile('fonts/Inter-Bold.otf')}');}
@font-face {font-family: 'Inter'; font-weight: 900; src: url('${staticFile('fonts/Inter-Black.otf')}');}
`;

// Slowly drifting glow blobs driven by noise so the background never sits still.
const Background: React.FC<{colors: ReelConfig['colors']}> = ({colors}) => {
  const frame = useCurrentFrame();
  const blobs = [0, 1, 2].map((i) => {
    const x = 50 + noise2D(`x${i}`, frame / 220, i) * 35;
    const y = 30 + i * 22 + noise2D(`y${i}`, frame / 260, i) * 12;
    return `radial-gradient(circle at ${x}% ${y}%, ${colors.accent}${i === 1 ? '40' : '2e'} 0%, transparent 38%)`;
  });
  return (
    <AbsoluteFill
      style={{background: `${blobs.join(',')}, linear-gradient(180deg, ${colors.bg_top}, ${colors.bg_bottom})`}}
    >
      {/* subtle grid for depth */}
      <AbsoluteFill
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.035) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.035) 2px, transparent 2px)',
          backgroundSize: '90px 90px',
          backgroundPosition: `0 ${frame * 0.6}px`,
          maskImage: 'radial-gradient(circle at 50% 50%, black 20%, transparent 75%)',
        }}
      />
    </AbsoluteFill>
  );
};

const Kicker: React.FC<{text: string; colors: ReelConfig['colors']}> = ({text, colors}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 180}});
  const chars = text.split('');
  return (
    <div
      style={{
        alignSelf: 'center',
        background: colors.accent,
        padding: '18px 40px',
        borderRadius: 999,
        transform: `scale(${pop}) rotate(${interpolate(pop, [0, 1], [-8, 0])}deg)`,
        boxShadow: `0 0 60px ${colors.accent}88`,
        marginBottom: 70,
        fontWeight: 700,
        fontSize: 46,
        letterSpacing: 4,
        color: colors.text,
        display: 'flex',
      }}
    >
      {chars.map((c, i) => (
        <span key={i} style={{opacity: interpolate(frame, [4 + i * 0.8, 8 + i * 0.8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
          {c === ' ' ? ' ' : c}
        </span>
      ))}
    </div>
  );
};

// Each word springs up from below with a slight blur, staggered across lines.
const KineticLines: React.FC<{lines: string[]; colors: ReelConfig['colors']; delay: number}> = ({lines, colors, delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const longest = Math.max(...lines.map((l) => l.length));
  const fontSize = Math.min(130, Math.floor(1450 / Math.max(longest, 8)));
  let wordIndex = 0;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10}}>
      {lines.map((line, li) => (
        <div key={li} style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 0.28em', fontSize}}>
          {line.split(' ').map((word, wi) => {
            const start = delay + wordIndex++ * 3;
            const p = spring({frame: frame - start, fps, config: {damping: 14, stiffness: 140, mass: 0.7}});
            const highlight = li === lines.length - 1 && lines.length > 1;
            return (
              <span
                key={wi}
                style={{
                  display: 'inline-block',
                  fontWeight: 900,
                  fontSize,
                  lineHeight: 1.12,
                  color: highlight ? colors.accent : colors.text,
                  opacity: p,
                  filter: `blur(${(1 - p) * 12}px)`,
                  transform: `translateY(${(1 - p) * 90}px) scale(${0.85 + 0.15 * p})`,
                  textShadow: highlight ? `0 0 40px ${colors.accent}aa` : '0 8px 30px rgba(0,0,0,0.5)',
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

const CtaBox: React.FC<{keyword: string; colors: ReelConfig['colors']}> = ({keyword, colors}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - 14, fps, config: {damping: 9, stiffness: 160}});
  const pulse = 1 + 0.05 * Math.sin(((frame - 14) / fps) * Math.PI * 3.2) * Math.min(1, Math.max(0, (frame - 30) / 10));
  const shine = interpolate((frame - 30) % 45, [0, 25], [-120, 220], {extrapolateRight: 'clamp'});
  const sub = spring({frame: frame - 30, fps, config: {damping: 200}});
  const arrow = Math.sin((frame / fps) * Math.PI * 4) * 14;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 50}}>
      <div
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: colors.accent,
          borderRadius: 40,
          padding: '34px 90px',
          transform: `scale(${enter * pulse})`,
          boxShadow: `0 20px 90px ${colors.accent}aa`,
          fontWeight: 900,
          fontSize: 150,
          color: colors.text,
        }}
      >
        “{keyword}”
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${shine}%`,
            width: '40%',
            background: 'linear-gradient(100deg, transparent, rgba(255,255,255,0.45), transparent)',
            transform: 'skewX(-20deg)',
          }}
        />
      </div>
      <div style={{marginTop: 50, fontWeight: 500, fontSize: 52, color: colors.muted, opacity: sub, transform: `translateY(${(1 - sub) * 30}px)`}}>
        aur link seedha aapke DM mein 📩
      </div>
      <div style={{marginTop: 40, fontSize: 90, opacity: sub, transform: `translateY(${arrow}px)`}}>👇</div>
    </div>
  );
};

const SceneView: React.FC<{scene: Scene; cfg: ReelConfig}> = ({scene, cfg}) => (
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '0 70px', display: 'flex', flexDirection: 'column'}}>
    {scene.kicker ? <Kicker text={scene.kicker} colors={cfg.colors} /> : null}
    <KineticLines lines={scene.lines} colors={cfg.colors} delay={8} />
    {scene.cta ? <CtaBox keyword={cfg.keyword} colors={cfg.colors} /> : null}
  </AbsoluteFill>
);

const Chrome: React.FC<{cfg: ReelConfig}> = ({cfg}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 200}});
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', top: 110, left: 70, right: 70, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.15)'}}>
        <div style={{width: `${(frame / durationInFrames) * 100}%`, height: '100%', borderRadius: 4, background: cfg.colors.accent, boxShadow: `0 0 20px ${cfg.colors.accent}`}} />
      </div>
      <div style={{position: 'absolute', top: 150, left: 70, display: 'flex', alignItems: 'center', gap: 14, opacity: intro, transform: `translateX(${(1 - intro) * -40}px)`}}>
        <span style={{fontWeight: 900, fontSize: 56, color: cfg.colors.accent, letterSpacing: 1}}>{cfg.brand}</span>
        <span style={{width: 20, height: 20, borderRadius: 10, background: cfg.colors.accent, transform: `scale(${1 + 0.25 * Math.sin(frame / 6)})`}} />
      </div>
      <div style={{position: 'absolute', bottom: 300, width: '100%', textAlign: 'center', fontWeight: 500, fontSize: 40, color: cfg.colors.muted, opacity: intro}}>
        {cfg.handle}
      </div>
    </AbsoluteFill>
  );
};

export const BeastReel: React.FC<ReelConfig> = (cfg) => {
  const {fps} = useVideoConfig();
  // Transitions overlap neighbouring scenes, so pad every scene but the last
  // to keep the total length equal to the sum of configured durations.
  return (
    <AbsoluteFill style={{fontFamily: 'Inter, sans-serif'}}>
      <style>{fontFaces}</style>
      <Background colors={cfg.colors} />
      <TransitionSeries>
        {cfg.scenes.flatMap((scene, i) => {
          const last = i === cfg.scenes.length - 1;
          const frames = Math.round(scene.duration * fps) + (last ? 0 : TRANSITION);
          const seq = (
            <TransitionSeries.Sequence key={`s${i}`} durationInFrames={frames}>
              <SceneView scene={scene} cfg={cfg} />
            </TransitionSeries.Sequence>
          );
          if (last) return [seq];
          return [
            seq,
            <TransitionSeries.Transition
              key={`t${i}`}
              presentation={slide({direction: i % 2 ? 'from-left' : 'from-right'})}
              timing={linearTiming({durationInFrames: TRANSITION})}
            />,
          ];
        })}
      </TransitionSeries>
      <Chrome cfg={cfg} />
    </AbsoluteFill>
  );
};
