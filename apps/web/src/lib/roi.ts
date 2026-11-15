/** Pure spherical geometry; no HTTP or viewer lifecycle dependencies. */
export type Coordinate = { ra: number; dec: number };
export type Region = { center: Coordinate; corners: Coordinate[]; width_arcmin: number; height_arcmin: number };
export type RoiView = {
  pix2world(x: number, y: number, frame?: string): number[] | null | undefined;
  world2pix(ra: number, dec: number, frame?: string): number[] | null | undefined;
  getRaDec(): number[];
  getSize?(): number[];
  gotoRaDec(ra: number, dec: number): void;
  setFoV(degrees: number): void;
};
const rad = Math.PI / 180;
export function separation(a: Coordinate, b: Coordinate): number {
  const x = Math.sin((b.dec-a.dec)*rad/2)**2 + Math.cos(a.dec*rad)*Math.cos(b.dec*rad)*Math.sin((b.ra-a.ra)*rad/2)**2;
  return 2*Math.atan2(Math.sqrt(Math.max(0,x)), Math.sqrt(Math.max(0,1-x))) / rad * 60;
}
export function coordinate(p: number[] | null | undefined): Coordinate {
  if (!p || !Number.isFinite(p[0]) || !Number.isFinite(p[1]) || Math.abs(p[1]) > 90) throw new Error("Punto fuera de la proyección celeste.");
  return { ra: ((p[0] % 360)+360)%360, dec: p[1] };
}
export function makeRegion(center: Coordinate, corners: Coordinate[], max = 20): Region {
  const width_arcmin = Math.max(separation(corners[0],corners[1]),separation(corners[2],corners[3]));
  const height_arcmin = Math.max(separation(corners[1],corners[2]),separation(corners[3],corners[0]));
  if (Math.min(width_arcmin,height_arcmin) < .001) throw new Error("Arrastra para seleccionar un área mayor.");
  if (Math.max(width_arcmin,height_arcmin) > max) throw new Error(`Máximo ${max} × ${max} minutos de arco. Acércate al cielo y vuelve a dibujar.`);
  return {center,corners,width_arcmin,height_arcmin};
}
export function screenRegion(view: RoiView, a: number[], b: number[], max = 20): Region {
  const left=Math.min(a[0],b[0]), right=Math.max(a[0],b[0]), top=Math.min(a[1],b[1]), bottom=Math.max(a[1],b[1]);
  return makeRegion(coordinate(view.pix2world((left+right)/2,(top+bottom)/2,"ICRS")),
    [[left,top],[right,top],[right,bottom],[left,bottom]].map(([x,y])=>coordinate(view.pix2world(x,y,"ICRS"))),max);
}
export function defaultRegion(center: Coordinate, size = 10, max = 20): Region {
  // Inverse gnomonic projection in the center's east/north basis, valid at the poles too.
  const ra=center.ra*rad, dec=center.dec*rad, half=Math.tan(size/120*rad);
  const c=[Math.cos(dec)*Math.cos(ra),Math.cos(dec)*Math.sin(ra),Math.sin(dec)];
  const e=[-Math.sin(ra),Math.cos(ra),0], n=[-Math.sin(dec)*Math.cos(ra),-Math.sin(dec)*Math.sin(ra),Math.cos(dec)];
  const corners=[[-1,1],[1,1],[1,-1],[-1,-1]].map(([x,y])=>{
    const v=c.map((v,i)=>v+half*x*e[i]+half*y*n[i]);
    return coordinate([Math.atan2(v[1],v[0])/rad,Math.atan2(v[2],Math.hypot(v[0],v[1]))/rad]);
  });
  return makeRegion(center,corners,max);
}

function vector(p: Coordinate): number[] {
  return [Math.cos(p.dec*rad)*Math.cos(p.ra*rad), Math.cos(p.dec*rad)*Math.sin(p.ra*rad), Math.sin(p.dec*rad)];
}
const dot = (a: number[], b: number[]) => a.reduce((sum,v,i)=>sum+v*b[i],0);
const cross = (a: number[], b: number[]) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
function fromVector(v: number[]): Coordinate {
  return coordinate([Math.atan2(v[1],v[0])/rad,Math.atan2(v[2],Math.hypot(v[0],v[1]))/rad]);
}

/** Rigid rotation on the sphere preserves all side lengths, including across RA=0. */
function rotateCoordinate(p: Coordinate, from: Coordinate, to: Coordinate): Coordinate {
  const a=vector(from), b=vector(to), axis=cross(a,b);
  const sine=Math.hypot(...axis), cosine=Math.max(-1,Math.min(1,dot(a,b)));
  if (cosine < -0.999999) throw new Error("Movimiento ambiguo al punto antipodal.");
  if (sine < 1e-14) return p;
  const n=axis.map(x=>x/sine), v=vector(p), nxv=cross(n,v);
  return fromVector(v.map((x,i)=>x*cosine+nxv[i]*sine+n[i]*dot(n,v)*(1-cosine)));
}
export function dragRegion(region: Region, from: Coordinate, to: Coordinate, max=20): Region {
  return makeRegion(rotateCoordinate(region.center,from,to),
    region.corners.map(p=>rotateCoordinate(p,from,to)),max+1e-8);
}
export function moveRegion(region: Region, center: Coordinate, max=20): Region {
  return {...dragRegion(region,region.center,center,max),center};
}

/** Resize about the opposite corner in a local tangent plane. No pixel-degree scaling. */
export function resizeRegion(region: Region, index: number, pointer: Coordinate, max=20): Region {
  const c=vector(region.center), r=region.center.ra*rad, d=region.center.dec*rad;
  const east=[-Math.sin(r),Math.cos(r),0], north=[-Math.sin(d)*Math.cos(r),-Math.sin(d)*Math.sin(r),Math.cos(d)];
  const project=(p:Coordinate)=>{
    const v=vector(p), denominator=dot(c,v);
    if(denominator<=0) throw new Error("Punto fuera del plano de selección.");
    return [dot(v,east)/denominator,dot(v,north)/denominator];
  };
  const unproject=(p:number[])=>fromVector(c.map((x,i)=>x+p[0]*east[i]+p[1]*north[i]));
  const corners=region.corners.map(project), opposite=(index+2)%4, anchor=corners[opposite];
  const unit=(p:number[])=>{const v=p.map((x,i)=>x-anchor[i]),len=Math.hypot(...v);return v.map(x=>x/len);};
  const u=unit(corners[(opposite+1)%4]), v=unit(corners[(opposite+3)%4]);
  const p=project(pointer).map((x,i)=>x-anchor[i]), det=u[0]*v[1]-u[1]*v[0];
  if(Math.abs(det)<1e-8)throw new Error("Selección degenerada.");
  // Spherical distance is at most tangent-plane distance; this bound cannot overshoot.
  const bound=max*rad/60, minimum=.02*rad/60;
  const a=Math.max(minimum,Math.min(bound,(p[0]*v[1]-p[1]*v[0])/det));
  const b=Math.max(minimum,Math.min(bound,(u[0]*p[1]-u[1]*p[0])/det));
  const points=[anchor,anchor.map((x,i)=>x+a*u[i]),anchor.map((x,i)=>x+a*u[i]+b*v[i]),anchor.map((x,i)=>x+b*v[i])];
  const next=region.corners.map((_,i)=>unproject(points[(i-opposite+4)%4]));
  return makeRegion(unproject(anchor.map((x,i)=>x+(a*u[i]+b*v[i])/2)),next,max);
}

/** Zoom changes only the view, never the stored celestial region. */
export function focusRegion(view: RoiView, region: Region, max=20, aspect=1): void {
  view.gotoRaDec(region.center.ra,region.center.dec);
  view.setFoV(max/60*1.8*Math.max(1,aspect));
}
