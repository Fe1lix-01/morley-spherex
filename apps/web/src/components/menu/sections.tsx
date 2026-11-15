import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { OrbitIcon } from "@/components/ui/CustomIcons";
import { eter } from "@/lib/theme";
import { PHENOMENA } from "@/data/phenomena";
import PhenomenonArt from "@/components/phenomena/PhenomenonArt";
import type { FilterDef } from "@/lib/viewer/types";
import { ABOUT, FILTERS_INTRO, PHENOMENA_INTRO } from "@/data/menuContent";

/** Estilo del texto pequeño en mayúsculas que va sobre los títulos. */
export const eyebrow = {
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.14em",
  color: "text.disabled",
} as const;

/* ------------------------------------------------------------------ */
/* Acerca de                                                           */
/* ------------------------------------------------------------------ */

export function AboutSection() {
  return (
    <Box>
      <Typography sx={eyebrow}>{ABOUT.eyebrow}</Typography>
      <Typography component="h3" sx={{ mt: 1.5, fontSize: 28, lineHeight: 1.2 }}>
        {ABOUT.title}
      </Typography>
      <Typography sx={{ mt: 2, fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{ABOUT.intro}</Typography>

      <Box
        sx={{
          mt: 2.5,
          p: 2.5,
          borderRadius: "16px",
          border: "1px solid rgba(255,255,255,0.12)",
          backgroundColor: eter.card,
        }}
      >
        <Typography sx={{ fontSize: 14 }}>{ABOUT.noteTitle}</Typography>
        <Typography sx={{ mt: 1, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.6)" }}>
          {ABOUT.note}
        </Typography>
      </Box>

      <Typography sx={{ mt: 2.5, fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{ABOUT.body}</Typography>

      <Box sx={{ mt: 2.5, display: "flex", alignItems: "center", gap: 1.5 }}>
        <OrbitIcon sx={{ fontSize: 28, color: "rgba(255,255,255,0.55)" }} />
        <Box>
          <Typography sx={{ fontSize: 15 }}>{ABOUT.mission}</Typography>
          <Typography sx={{ fontSize: 14, color: "text.disabled" }}>{ABOUT.missionSub}</Typography>
        </Box>
      </Box>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Filtros                                                             */
/* ------------------------------------------------------------------ */

export function FiltersSection({ filters, active }: { filters: FilterDef[]; active: number }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{FILTERS_INTRO}</Typography>
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, mt: 3 }}>
        {filters.map((f, i) => {
          const on = i === active;
          return (
            <Box
              component="li"
              key={f.id}
              sx={{ py: 2, borderBottom: `1px solid ${eter.line}`, "&:last-of-type": { borderBottom: 0 } }}
            >
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 1.5 }}>
                <Typography
                  component="p"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: 16,
                    color: on ? "primary.main" : "text.primary",
                  }}
                >
                  {on && (
                    <Box
                      component="span"
                      sx={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "primary.main" }}
                    />
                  )}
                  {f.name}
                </Typography>
                <Typography sx={{ flexShrink: 0, fontSize: 14, color: "text.disabled" }}>{f.band}</Typography>
              </Box>
              <Typography sx={{ mt: 0.75, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.6)" }}>
                {f.desc}
                {on && " Banda activa del visor."}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Fenómenos                                                           */
/* ------------------------------------------------------------------ */

export function PhenomenaSection() {
  return (
    <Box>
      <Typography sx={{ fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{PHENOMENA_INTRO}</Typography>
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, mt: 2, display: "grid", gap: 1.5 }}>
        {PHENOMENA.map((ph) => (
          <Box
            component="li"
            key={ph.id}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              p: 1.5,
              borderRadius: "16px",
              border: "1px solid rgba(255,255,255,0.12)",
              backgroundColor: eter.card,
            }}
          >
            {/* Si la foto no carga, Avatar muestra la ilustración SVG de respaldo (children). */}
            <Avatar
              variant="rounded"
              src={ph.image}
              alt=""
              sx={{ width: 76, height: 76, flexShrink: 0, borderRadius: "12px", backgroundColor: "#000" }}
            >
              <PhenomenonArt id={ph.id} />
            </Avatar>
            <Box>
              <Typography sx={{ fontSize: 16 }}>{ph.title}</Typography>
              <Typography sx={{ mt: 0.5, fontSize: 14, lineHeight: 1.4, color: "rgba(255,255,255,0.55)" }}>
                {ph.tagline}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}