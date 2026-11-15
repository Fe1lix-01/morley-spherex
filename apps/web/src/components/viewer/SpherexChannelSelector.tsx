
"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";

import {
  getSpherexChannel,
  SPHEREX_TOTAL_CHANNELS,
} from "@/data/spherexChannels";

type Props = {
  channel: number;
  onChange: (channel: number) => void;
  disabled?: boolean;
};

export default function SpherexChannelSelector({
  channel,
  onChange,
  disabled = false,
}: Props) {
  const info = getSpherexChannel(channel);

  return (
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          mb: 2,
          gap: 2,
        }}
      >
        <Box>
          <Typography
            sx={{
              fontSize: 11,
              letterSpacing: "0.08em",
              color: "#aab0c4",
            }}
          >
            CANAL ACTIVO
          </Typography>

          <Typography
            sx={{
              fontSize: 30,
              fontWeight: 700,
              color: "#fff",
            }}
          >
            {channel}
            <Box
              component="span"
              sx={{ fontSize: 16, color: "#aaa", ml: 1 }}
            >
              / {SPHEREX_TOTAL_CHANNELS}
            </Box>
          </Typography>
        </Box>

        <Box sx={{ textAlign: "right" }}>
          <Typography sx={{ fontSize: 11, color: "#aaa" }}>
            Longitud de onda
          </Typography>

          <Typography
            sx={{
              fontSize: 24,
              fontWeight: 600,
              color: "#fff",
            }}
          >
            {info.wavelengthUm.toFixed(3)} µm
          </Typography>
        </Box>
      </Box>

      <Slider
        min={1}
        max={102}
        step={1}
        value={channel}
        disabled={disabled}
        onChange={(_, value) => {
          if (typeof value === "number") {
            onChange(value);
          }
        }}
        aria-label="Canal espectral SPHEREx"
        sx={{
          color: "#fff",
          height: 8,
          "& .MuiSlider-rail": {
            backgroundColor: "#34343b",
            opacity: 1,
          },
          "& .MuiSlider-track": {
            border: "none",
            backgroundColor: "#777",
          },
          "& .MuiSlider-thumb": {
            width: 20,
            height: 20,
            backgroundColor: "#fff",
            boxShadow: "0 0 8px #0008",
          },
        }}
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
          gap: 0.5,
          mt: 1,
        }}
      >
        {[1, 2, 3, 4, 5, 6].map((band) => (
          <Button
            key={band}
            disabled={disabled}
            onClick={() => onChange((band - 1) * 17 + 1)}
            sx={{
              minWidth: 0,
              color: "#fff",
              borderRadius: 2,
              border:
                info.band === band
                  ? "1px solid #888"
                  : "1px solid transparent",
              backgroundColor:
                info.band === band
                  ? "#ffffff20"
                  : "transparent",
              "&:hover": {
                backgroundColor: "#ffffff18",
              },
            }}
          >
            B{band}
          </Button>
        ))}
      </Box>

      <Typography
        sx={{
          mt: 1.5,
          fontSize: 12,
          color: info.valid ? "#b4b4c4" : "#ffb86c",
        }}
      >
        {info.valid
          ? `Banda B${info.band} · Canal ${info.bandChannel}/17`
          : "Canal sin datos científicos válidos en DR1."}
      </Typography>
    </Box>
  );
}
