import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';

const [source, briefPath, output] = process.argv.slice(2);
if (!source || !briefPath || !output || process.argv.length !== 5) {
  console.error('Usage: node cover/render.mjs SOURCE.mp4 COVER.json OUTPUT_DIRECTORY');
  process.exit(2);
}
const layoutDir = path.dirname(fileURLToPath(import.meta.url));
const brief = JSON.parse(await fs.readFile(briefPath, 'utf8'));
const limits = {kicker:16, line1:7, line2:7, deck:21, card:12, claim:7, caption:18, footer:36};
const escape = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const fields = {};
for (const [key, limit] of Object.entries(limits)) {
  const value = brief[key];
  if (typeof value !== 'string' || !value.trim() || Array.from(value).length > limit)
    throw new Error('Expected 1 to '+limit+' characters for '+key);
  fields[key] = escape(value);
}
if (!Number.isFinite(brief.frameSeconds) || brief.frameSeconds < 0)
  throw new Error('frameSeconds must be a nonnegative number');
const crop = brief.crop;
if (crop && !['left','top','width','height'].every(k =>
    Number.isInteger(crop[k]) && crop[k] >= (['left','top'].includes(k) ? 0 : 1)))
  throw new Error('Invalid crop rectangle');

const destination = path.resolve(output);
await fs.mkdir(path.dirname(destination),{recursive:true});
try { await fs.access(destination); throw new Error('Choose a new cover output directory'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const staging = await fs.mkdtemp(path.join(path.dirname(destination),'.cover-'));
try {
  const frame = path.join(staging,'portrait.jpg');
  const proc = spawnSync(process.env.FFMPEG || 'ffmpeg',['-nostdin','-v','error','-ss',String(brief.frameSeconds),
    '-i',path.resolve(source),'-frames:v','1','-q:v','2',frame],{stdio:'inherit'});
  if (proc.error) throw proc.error;
  if (proc.status !== 0) throw new Error('FFmpeg frame extraction failed');
  let photo = sharp(frame).rotate();
  if (crop) photo=photo.extract(crop);
  const jpg=await photo.resize(462,648,{fit:'cover',position:'centre'}).jpeg({quality:96,chromaSubsampling:'4:4:4'}).toBuffer();
  fields.photo=jpg.toString('base64');
  for (const ratio of ['9x16','3x4']) {
    const template=await fs.readFile(path.join(layoutDir,ratio+'.svg'),'utf8');
    const svg=template.replace(/\{\{(\w+)\}\}/g,(_,name)=>{
      if (!(name in fields)) throw new Error('Unknown template field '+name);
      return fields[name];
    });
    const base=path.join(staging,'cover-'+ratio);
    await fs.writeFile(base+'.svg',svg);
    await sharp(Buffer.from(svg)).png().toFile(base+'.png');
    await sharp(Buffer.from(svg)).jpeg({quality:95,chromaSubsampling:'4:4:4'}).toFile(base+'.jpg');
  }
  await fs.rename(staging,destination);
} finally {
  await fs.rm(staging,{recursive:true,force:true});
}

