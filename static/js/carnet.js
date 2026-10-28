// Dibujo del carnet de voluntariado (formato vertical tipo tarjeta, 638 x 1010).
//
// Se dibuja en un <canvas>, por eso la MISMA función sirve para:
//   - la vista previa en vivo mientras el administrador llena el formulario,
//   - la página del carnet de cada persona,
//   - la descarga en PNG/JPG (se dibuja en alta resolución y se exporta).
//
// Los textos fijos (título, "VOLUNTARIO/A", frase del pie) vienen de config.py.
// El emblema del encabezado es static/img/emblema_blanco.png (logo de la organización,
// PNG blanco con fondo transparente).
(function (global) {
    "use strict";

    const W = 638;
    const H = 1010;

    const C = {
        marino: "#022249",
        turquesa: "#1799b4",
        turquesaClaro: "#25abc7",
        morado: "#6a5a8e",
        texto: "#12304e",
        negro: "#111827",
        rojo: "#b42318",
        gris: "#8a97a6",
    };
    const FUENTE = "Montserrat, 'Segoe UI', Roboto, Arial, sans-serif";

    // Posiciones (en las unidades del diseño de 638 x 1010).
    const FOTO_EXT = { x: 183, y: 150, w: 272, h: 272, r: 30 };
    const FOTO_INT = { x: 190, y: 157, w: 258, h: 258, r: 24 };
    const QR_CAJA = { x: 231, y: 797, w: 176, h: 176, r: 16 };

    let config = { entidad: "", titulo: "", rol: "", fraseFija: "" };
    let logoUrl = "";
    let recursosPromesa = null;

    // ---------------------------------------------------------------- utilidades

    function configurar(cfg, urlLogo) {
        config = Object.assign(config, cfg || {});
        logoUrl = urlLogo || logoUrl;
        recursosPromesa = null;
    }

    function cargarImagen(url) {
        return new Promise((resolve) => {
            if (!url) { resolve(null); return; }
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => resolve(null);
            img.src = url;
        });
    }

    // Carga las tipografías y el logo (una sola vez).
    function cargarRecursos() {
        if (!recursosPromesa) {
            const fuentes = ["500", "600", "700", "800"].map((peso) =>
                document.fonts && document.fonts.load
                    ? document.fonts.load(`${peso} 20px Montserrat`)
                    : Promise.resolve()
            );
            recursosPromesa = Promise.all([
                Promise.allSettled(fuentes),
                cargarImagen(logoUrl),
            ]).then(([, logo]) => ({ logo }));
        }
        return recursosPromesa;
    }

    function fmtFecha(iso) {
        const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
        return m ? `${m[3]}/${m[2]}/${m[1]}` : "";
    }

    function hoyISO() {
        const d = new Date();
        const dos = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
    }

    // Mismo criterio que models.estado_credencial() en el servidor.
    function estadoCredencial(desde, hasta, activo) {
        if (activo === false) return "Inactivo";
        const hoy = hoyISO();
        if (hasta && hoy > hasta) return "Vencido";
        if (desde && hoy < desde) return "Por iniciar";
        return "Activo";
    }

    function rr(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    function fuente(peso, tam) { return `${peso} ${tam}px ${FUENTE}`; }

    function medir(ctx, texto, peso, tam) {
        ctx.font = fuente(peso, tam);
        return ctx.measureText(texto).width;
    }

    // Tamaño de letra más grande (hasta `max`) con el que el texto cabe en `ancho`.
    function ajustar(ctx, texto, peso, max, min, ancho) {
        let tam = max;
        while (tam > min && medir(ctx, texto, peso, tam) > ancho) tam -= 1;
        return tam;
    }

    function lineas(ctx, texto, peso, tam, ancho) {
        ctx.font = fuente(peso, tam);
        const palabras = texto.split(/\s+/).filter(Boolean);
        const salida = [];
        let actual = "";
        for (const palabra of palabras) {
            const prueba = actual ? `${actual} ${palabra}` : palabra;
            if (actual && ctx.measureText(prueba).width > ancho) {
                salida.push(actual);
                actual = palabra;
            } else {
                actual = prueba;
            }
        }
        if (actual) salida.push(actual);
        return salida;
    }

    function escribir(ctx, texto, x, y, peso, tam, color, alinear) {
        ctx.font = fuente(peso, tam);
        ctx.fillStyle = color;
        ctx.textAlign = alinear || "left";
        ctx.textBaseline = "alphabetic";
        ctx.fillText(texto, x, y);
    }

    // ------------------------------------------------------------------ fondo

    function laurel(ctx, cx, baseY, dir) {
        ctx.save();
        ctx.translate(cx, baseY);
        ctx.scale(dir, 1);
        ctx.fillStyle = "rgba(110, 150, 205, 0.065)";
        const n = 9;
        for (let i = 0; i < n; i++) {
            const t = i / (n - 1);
            const x = 10 * Math.sin(t * Math.PI * 0.9);
            const y = -t * 215;
            const largo = 26 - 8 * t;
            const ancho = 8.5 - 2.5 * t;
            [-0.95 - 0.25 * t, -2.2 + 0.1 * t].forEach((ang) => {
                ctx.beginPath();
                ctx.ellipse(x + Math.cos(ang) * largo, y + Math.sin(ang) * largo, largo, ancho, ang, 0, Math.PI * 2);
                ctx.fill();
            });
        }
        ctx.restore();
    }

    function dibujarEncabezado(ctx, recursos) {
        // Turquesa hasta la curva blanca y, encima, el azul marino un poco más arriba.
        const grad = ctx.createLinearGradient(0, 0, W, 0);
        grad.addColorStop(0, "#22aecb");
        grad.addColorStop(1, "#0f8db0");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(W, 0);
        ctx.lineTo(W, 192);
        ctx.bezierCurveTo(470, 108, 180, 104, 0, 198);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = C.marino;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(W, 0);
        ctx.lineTo(W, 188);
        ctx.bezierCurveTo(470, 104, 180, 95, 0, 186);
        ctx.closePath();
        ctx.fill();

        // Título en dos líneas: la última palabra baja a la segunda línea.
        const palabras = (config.titulo || "").split(/\s+/).filter(Boolean);
        const l1 = palabras.length > 1 ? palabras.slice(0, -1).join(" ") : palabras.join(" ");
        const l2 = palabras.length > 1 ? palabras[palabras.length - 1] : "";
        const tam = ajustar(ctx, l1.length > l2.length ? l1 : l2, 700, 40, 22, 300);
        escribir(ctx, l1, 18, 58, 700, tam, "#ffffff");
        if (l2) escribir(ctx, l2, 18, 97, 700, tam, "#ffffff");

        // Logo + nombre de la organización.
        if (recursos.logo) {
            // El emblema es más ancho que alto: se ajusta a una caja de 92 x 70
            // conservando sus proporciones y centrado junto al nombre.
            const cajaW = 92, cajaH = 70, cx = 374, cy = 63;
            const k = Math.min(cajaW / recursos.logo.naturalWidth, cajaH / recursos.logo.naturalHeight);
            const w = recursos.logo.naturalWidth * k, h = recursos.logo.naturalHeight * k;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(recursos.logo, cx - w / 2, cy - h / 2, w, h);
        }
        const nombre = (config.entidad || "").trim();
        const espacio = nombre.indexOf(" ");
        const e1 = espacio > 0 ? nombre.slice(0, espacio) : nombre;
        const e2 = espacio > 0 ? nombre.slice(espacio + 1) : "";
        const tamE = ajustar(ctx, e2.length > e1.length ? e2 : e1, 600, 21, 11, 195);
        escribir(ctx, e1, 431, e2 ? 73 : 86, 600, tamE, "#ffffff");
        if (e2) escribir(ctx, e2, 431, 98, 600, tamE, "#ffffff");
    }

    function dibujarOlas(ctx) {
        const g = ctx.createLinearGradient(0, H, W, H - 190);
        g.addColorStop(0, "#08689f");
        g.addColorStop(1, "#05a0c2");

        // Franjas de la derecha (blanca y turquesa), detrás de la ola principal.
        const franja = (desfase, ancho, color) => {
            ctx.strokeStyle = color;
            ctx.lineWidth = ancho;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(400, H - 34 - desfase);
            ctx.bezierCurveTo(480, H - 70 - desfase, 560, H - 130 - desfase, W + 10, H - 190 - desfase);
            ctx.stroke();
        };
        franja(16, 11, "#27b9d6");
        franja(7, 6, "#ffffff");

        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.moveTo(0, H - 92);
        ctx.bezierCurveTo(60, H - 108, 150, H - 100, 235, H - 58);
        ctx.lineTo(405, H - 34);
        ctx.bezierCurveTo(480, H - 70, 560, H - 130, W, H - 190);
        ctx.lineTo(W, H);
        ctx.lineTo(0, H);
        ctx.closePath();
        ctx.fill();

        // Línea clara sobre el borde izquierdo de la ola.
        ctx.strokeStyle = "#2bbad7";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(0, H - 98);
        ctx.bezierCurveTo(60, H - 114, 150, H - 106, 232, H - 63);
        ctx.stroke();

        // Puntitos de textura en la esquina inferior izquierda.
        ctx.fillStyle = "rgba(255,255,255,0.14)";
        for (let y = H - 52; y < H; y += 7) {
            for (let x = 8; x < 215; x += 7) {
                ctx.fillRect(x, y, 2, 2);
            }
        }
    }

    // ------------------------------------------------------------------- foto

    // Cuánto "sobra" de la foto (en unidades del diseño) una vez ampliada.
    function sobranteFoto(img, zoom) {
        const base = Math.max(FOTO_INT.w / img.naturalWidth, FOTO_INT.h / img.naturalHeight);
        const s = base * zoom;
        return {
            escala: s,
            sobraX: Math.max(0, img.naturalWidth * s - FOTO_INT.w),
            sobraY: Math.max(0, img.naturalHeight * s - FOTO_INT.h),
        };
    }

    function dibujarFoto(ctx, datos, marcadores) {
        const e = FOTO_EXT;
        const i = FOTO_INT;

        ctx.save();
        ctx.shadowColor = "rgba(2, 34, 73, 0.18)";
        ctx.shadowBlur = 14;
        ctx.shadowOffsetY = 3;
        rr(ctx, e.x, e.y, e.w, e.h, e.r);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
        ctx.restore();
        rr(ctx, e.x, e.y, e.w, e.h, e.r);
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#1f9db8";
        ctx.stroke();

        ctx.save();
        rr(ctx, i.x, i.y, i.w, i.h, i.r);
        ctx.clip();
        if (datos.foto) {
            const { escala, sobraX, sobraY } = sobranteFoto(datos.foto, datos.fotoZoom || 1);
            const px = datos.fotoX == null ? 0.5 : datos.fotoX;
            const py = datos.fotoY == null ? 0.3 : datos.fotoY;
            const dw = datos.foto.naturalWidth * escala;
            const dh = datos.foto.naturalHeight * escala;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(datos.foto, i.x - sobraX * px, i.y - sobraY * py, dw, dh);
        } else {
            ctx.fillStyle = "#eef2f6";
            ctx.fillRect(i.x, i.y, i.w, i.h);
            ctx.fillStyle = "#c9d3de";
            ctx.beginPath();
            ctx.arc(i.x + i.w / 2, i.y + 100, 40, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.ellipse(i.x + i.w / 2, i.y + 215, 80, 62, 0, 0, Math.PI * 2);
            ctx.fill();
            escribir(ctx, marcadores ? "Sube una foto" : "Sin foto", i.x + i.w / 2, i.y + 244, 600, 16, C.gris, "center");
        }
        ctx.restore();
    }

    // ------------------------------------------------------------------ iconos

    function iconoEstado(ctx, cx, cy) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.strokeStyle = "#1d1d1f";
        ctx.lineWidth = 2.6;
        ctx.beginPath();
        ctx.arc(0, 0, 19, 0, Math.PI * 2);
        ctx.stroke();
        ctx.lineWidth = 4.2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(-8.5, 1);
        ctx.lineTo(-2.5, 7.5);
        ctx.lineTo(9, -6.5);
        ctx.stroke();
        ctx.restore();
    }

    function iconoCalendario(ctx, cx, cy) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.strokeStyle = "#1d1d1f";
        ctx.fillStyle = "#1d1d1f";
        ctx.lineWidth = 2.6;
        ctx.lineCap = "round";
        rr(ctx, -15, -12, 30, 29, 5);
        ctx.stroke();
        rr(ctx, -15, -12, 30, 9, 4);
        ctx.fill();
        ctx.lineWidth = 3.4;
        [-8, 8].forEach((x) => {
            ctx.beginPath();
            ctx.moveTo(x, -17);
            ctx.lineTo(x, -9);
            ctx.stroke();
        });
        for (let f = 0; f < 2; f++) {
            for (let c = 0; c < 3; c++) {
                ctx.fillRect(-10 + c * 8, 2 + f * 7.5, 5, 4.5);
            }
        }
        ctx.restore();
    }

    function iconoContacto(ctx, cx, cy) {
        ctx.save();
        ctx.translate(cx - 2, cy + 2);
        ctx.strokeStyle = "#1d1d1f";
        ctx.lineWidth = 2.1;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        // Teléfono (trazo tipo "feather").
        ctx.save();
        ctx.scale(1.3, 1.3);
        ctx.translate(-11, -10);
        ctx.lineWidth = 2.1 / 1.3;
        ctx.stroke(new Path2D(
            "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 " +
            "19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 " +
            "2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 " +
            "2.81.7A2 2 0 0 1 22 16.92z"
        ));
        ctx.restore();
        // Globo con sirena de emergencia.
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(11, -12, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.lineWidth = 1.8;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(11, -11.5, 4, Math.PI, 0);
        ctx.lineTo(15, -8.5);
        ctx.lineTo(7, -8.5);
        ctx.closePath();
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(11, -19);
        ctx.lineTo(11, -17.2);
        ctx.moveTo(4.6, -14.2);
        ctx.lineTo(5.9, -13.4);
        ctx.moveTo(17.4, -14.2);
        ctx.lineTo(16.1, -13.4);
        ctx.stroke();
        ctx.restore();
    }

    // ------------------------------------------------------------- bloques de datos

    function dibujarNombreYRol(ctx, nombre, marcadores) {
        const hayNombre = !!nombre;
        const texto = (hayNombre ? nombre : "Nombres y apellidos").toLocaleUpperCase("es");
        const color = hayNombre ? C.negro : "#b8c1cc";
        const ancho = 560;

        let tam = ajustar(ctx, texto, 800, 34, 25, ancho);
        if (medir(ctx, texto, 800, tam) <= ancho) {
            escribir(ctx, texto, W / 2, 462, 800, tam, color, "center");
        } else {
            // Nombre muy largo: se parte en dos líneas.
            tam = 24;
            let partes = lineas(ctx, texto, 800, tam, ancho);
            if (partes.length > 2) partes = [partes[0], partes.slice(1).join(" ")];
            partes.forEach((linea, idx) => {
                const t = ajustar(ctx, linea, 800, tam, 14, ancho);
                escribir(ctx, linea, W / 2, 447 + idx * 26, 800, t, color, "center");
            });
        }

        // "VOLUNTARIO/A" con líneas decorativas a los lados.
        const rol = config.rol || "";
        const tw = medir(ctx, rol, 700, 30);
        escribir(ctx, rol, W / 2, 501, 700, 30, C.turquesaClaro, "center");
        ctx.strokeStyle = C.turquesaClaro;
        ctx.fillStyle = C.turquesaClaro;
        ctx.lineWidth = 2;
        [-1, 1].forEach((lado) => {
            const interior = W / 2 + lado * (tw / 2 + 9);
            const exterior = interior + lado * 72;
            ctx.beginPath();
            ctx.moveTo(interior, 493);
            ctx.lineTo(exterior, 493);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(exterior, 493, 5, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    function dibujarTipo(ctx, tipo, marcadores) {
        const hayTipo = !!tipo;
        if (!hayTipo && !marcadores) return;
        const texto = hayTipo ? tipo : "Tipo de voluntariado";
        const tam = ajustar(ctx, texto, 600, 17, 12, 380);
        const ancho = Math.max(190, Math.min(430, medir(ctx, texto, 600, tam) + 44));
        ctx.save();
        if (!hayTipo) ctx.globalAlpha = 0.35;
        rr(ctx, W / 2 - ancho / 2, 514, ancho, 33, 12);
        ctx.fillStyle = C.morado;
        ctx.fill();
        escribir(ctx, texto, W / 2, 536, 600, tam, "#ffffff", "center");
        ctx.restore();
    }

    function fila(ctx, baseY, etiqueta, valor, color, vacio, marcadores) {
        const xEtiqueta = 170;
        escribir(ctx, etiqueta, xEtiqueta, baseY, 700, 17, C.turquesa);
        const xValor = xEtiqueta + medir(ctx, etiqueta, 700, 17) + 9;
        const hayValor = !!valor;
        const texto = hayValor ? valor : (marcadores ? vacio : "—");
        const tam = ajustar(ctx, texto, 500, 18, 12, 540 - xValor);
        escribir(ctx, texto, xValor, baseY, 500, tam, hayValor ? color : "#b8c1cc");
    }

    function dibujarFilas(ctx, datos, marcadores) {
        iconoEstado(ctx, 137, 582);
        iconoCalendario(ctx, 137, 626);
        iconoContacto(ctx, 137, 672);

        const estado = datos.estado || "Activo";
        const colorEstado = estado === "Activo" || estado === "Por iniciar" ? C.texto : C.rojo;
        fila(ctx, 580, "Estado:", estado, colorEstado, "Activo", marcadores);

        const desde = fmtFecha(datos.desde);
        const hasta = fmtFecha(datos.hasta);
        const vigencia = desde && hasta ? `${desde} - ${hasta}` : "";
        fila(ctx, 632, "Vigencia:", vigencia, C.texto, "dd/mm/aaaa - dd/mm/aaaa", marcadores);

        const contacto = [datos.contactoNombre, datos.contactoTelefono].filter(Boolean).join(" - ");
        fila(ctx, 679, "Contacto:", contacto, C.texto, "Nombre - Teléfono", marcadores);

        // Separadores: dos punteados y uno continuo.
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = "#d3d9e0";
        ctx.setLineDash([2, 3]);
        [601, 651].forEach((y) => {
            ctx.beginPath();
            ctx.moveTo(114, y);
            ctx.lineTo(540, y);
            ctx.stroke();
        });
        ctx.setLineDash([]);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#cfd6df";
        ctx.beginPath();
        ctx.moveTo(114, 700);
        ctx.lineTo(540, 700);
        ctx.stroke();
    }

    function dibujarFrases(ctx, datos, marcadores) {
        // Frase del voluntario (opcional), máximo dos líneas.
        const hayFrase = !!datos.frase;
        if (hayFrase || marcadores) {
            const texto = `“${hayFrase ? datos.frase : "Frase o detalle propio (opcional)"}”`;
            let tam = 18;
            let partes = lineas(ctx, texto, 500, tam, 540);
            while (partes.length > 2 && tam > 12) {
                tam -= 1;
                partes = lineas(ctx, texto, 500, tam, 540);
            }
            if (partes.length > 2) partes = [partes[0], partes[1].replace(/\s*\S*$/, "") + "…"];
            const base = partes.length === 1 ? 735 : 725;
            ctx.save();
            if (!hayFrase) ctx.globalAlpha = 0.35;
            partes.forEach((linea, idx) => {
                escribir(ctx, linea, W / 2, base + idx * 22, 500, tam, "#1d2330", "center");
            });
            ctx.restore();
        }

        // Frase fija al pie.
        const fija = lineas(ctx, config.fraseFija || "", 600, 10.5, 430);
        fija.slice(0, 3).forEach((linea, idx) => {
            escribir(ctx, linea, W / 2, 773 + idx * 14, 600, 10.5, "#1c3b5e", "center");
        });
    }

    function dibujarQR(ctx, qr) {
        const c = QR_CAJA;
        ctx.save();
        ctx.shadowColor = "rgba(2, 34, 73, 0.22)";
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 3;
        rr(ctx, c.x, c.y, c.w, c.h, c.r);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
        ctx.restore();
        rr(ctx, c.x, c.y, c.w, c.h, c.r);
        ctx.lineWidth = 3;
        ctx.strokeStyle = "#1f9db8";
        ctx.stroke();
        if (qr) {
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(qr, c.x + 7, c.y + 7, c.w - 14, c.h - 14);
        }
    }

    // ----------------------------------------------------------------- principal

    // datos: { nombre, tipo, desde, hasta (AAAA-MM-DD), estado, contactoNombre,
    //          contactoTelefono, frase, foto (Image|null), fotoZoom, fotoX, fotoY,
    //          qr (Image|null) }
    // opciones: { escala = 1, marcadores = false }  (marcadores: muestra textos
    //          de ejemplo en gris para los campos vacíos, solo en la vista previa)
    function dibujar(canvas, datos, recursos, opciones) {
        const o = Object.assign({ escala: 1, marcadores: false }, opciones);
        canvas.width = Math.round(W * o.escala);
        canvas.height = Math.round(H * o.escala);
        const ctx = canvas.getContext("2d");
        ctx.setTransform(o.escala, 0, 0, o.escala, 0, 0);
        ctx.clearRect(0, 0, W, H);

        ctx.fillStyle = "#fefefd";
        ctx.fillRect(0, 0, W, H);
        laurel(ctx, 48, 470, 1);
        laurel(ctx, W - 48, 470, -1);

        dibujarOlas(ctx);
        dibujarEncabezado(ctx, recursos);
        dibujarFoto(ctx, datos, o.marcadores);
        dibujarNombreYRol(ctx, datos.nombre, o.marcadores);
        dibujarTipo(ctx, datos.tipo, o.marcadores);
        dibujarFilas(ctx, datos, o.marcadores);
        dibujarFrases(ctx, datos, o.marcadores);
        dibujarQR(ctx, datos.qr);
    }

    // Dibuja el carnet en alta resolución y lo devuelve como archivo (Blob).
    function exportar(datos, recursos, formato, escala) {
        const lienzo = document.createElement("canvas");
        dibujar(lienzo, datos, recursos, { escala: escala || 2, marcadores: false });
        const tipo = formato === "jpeg" ? "image/jpeg" : "image/png";
        return new Promise((resolve, reject) => {
            lienzo.toBlob(
                (blob) => (blob ? resolve(blob) : reject(new Error("No se pudo generar la imagen."))),
                tipo,
                0.93
            );
        });
    }

    function nombreArchivo(nombre, extension) {
        const limpio = (nombre || "persona")
            .normalize("NFD").replace(/[̀-ͯ]/g, "")
            .replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        return `Carnet_${limpio || "persona"}.${extension}`;
    }

    global.Carnet = {
        ANCHO: W, ALTO: H, FOTO: FOTO_INT,
        configurar, cargarRecursos, cargarImagen, dibujar, exportar,
        estadoCredencial, sobranteFoto, nombreArchivo, fmtFecha,
    };
})(window);
