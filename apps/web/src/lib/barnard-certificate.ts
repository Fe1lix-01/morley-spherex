import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

export async function personalizeBarnardCertificate(template: ArrayBuffer | Uint8Array, input: string): Promise<Uint8Array> {
  const name = input.normalize("NFC").trim().replace(/\s+/g, " ");
  if (!name) throw new Error("Escribe tu nombre completo.");
  if (name.length > 100) throw new Error("El nombre debe tener como máximo 100 caracteres.");
  const pdf = await PDFDocument.load(template);
  const page = pdf.getPages()[0];
  if (!page || pdf.getPageCount() !== 1 || Math.abs(page.getWidth() - 842) > 1 || Math.abs(page.getHeight() - 595) > 1) {
    throw new Error("La plantilla no corresponde al certificado de Barnard.");
  }
  const font = await pdf.embedFont(StandardFonts.TimesRoman);
  let width: number;
  try {
    width = font.widthOfTextAtSize(name, 31);
  } catch {
    throw new Error("Usa letras del alfabeto latino (se permiten acentos y ñ), espacios, guiones o apóstrofes.");
  }
  const size = Math.min(31, 680 * 31 / width);
  if (size < 12) throw new Error("El nombre es demasiado largo para el certificado. Usa una versión más corta.");
  page.drawText(name, {
    x: (page.getWidth() - font.widthOfTextAtSize(name, size)) / 2,
    y: 286,
    size,
    font,
    color: rgb(243 / 255, 239 / 255, 231 / 255),
  });
  pdf.setTitle(`Project Morley | Certificado - ${name}`);
  pdf.setAuthor("Project Morley");
  return pdf.save();
}
