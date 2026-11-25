import Constants from 'expo-constants';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Image, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api } from '../api';
import { useAuth } from '../auth';
import { CONTACT_EMAIL } from '../legal';
import { c, font } from '../theme';
import { Header, Icon } from '../ui';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

// "2026-11-12" → "12 nov 2026" (sin pasar por Date: evita correr un día por zona horaria).
function fecha(iso: string | null | undefined): string | null {
  const m = iso?.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${Number(m[3])} ${MESES[Number(m[2]) - 1]} ${m[1]}` : null;
}

const SOURCES = [
  { icon: 'ranking', title: 'Ranking público de FECNA', text: 'Se sincroniza cada semana y cuando un administrador lo pide.' },
  { icon: 'chat', title: 'Las cifras las calcula el sistema', text: 'El chat con IA solo explica los resultados; no inventa marcas.' },
  { icon: 'target', title: 'Marcas mínimas', text: 'Reglamento FECNA 2026, art. 13 · piscina larga (50 m).' },
];

// Se abre desde Perfil (diseño "Acerca de").
export default function Acerca() {
  const { user } = useAuth();
  const [dataUntil, setDataUntil] = useState<string | null>(null);
  const version = Constants.expoConfig?.version;

  useEffect(() => {
    if (user) api('/me').then((me) => setDataUntil(fecha(me.data_until))).catch(() => {});
  }, [user]);

  const back = () => (router.canGoBack() ? router.back() : router.replace('/'));
  const mail = () => Linking.openURL(`mailto:${CONTACT_EMAIL}?subject=NATIA`).catch(() => {});

  return (
    <View style={s.root}>
      <Header title="Acerca de" onBack={back} />
      <ScrollView contentContainerStyle={{ padding: 16, paddingTop: 20, gap: 12 }}>
        <View style={s.hero}>
          <Image source={require('../../assets/splash-icon.png')} style={s.logo} accessibilityLabel="Ícono de NATIA" />
          <Text style={s.name}>NATIA</Text>
          <Text style={s.tagline}>Tu asistente de natación</Text>
          <Text style={s.desc}>Consulta rankings, mejores marcas, mínimas y la evolución de cada nadador preguntando en lenguaje natural.</Text>
          <View style={s.pills}>
            {version ? <Text style={s.pill}>Versión {version}</Text> : null}
            {dataUntil ? <Text style={s.pill}>Datos al {dataUntil}</Text> : null}
          </View>
        </View>

        <Text style={s.h}>DE DÓNDE SALEN LOS DATOS</Text>
        <View style={[s.card, { paddingVertical: 4 }]}>
          {SOURCES.map((it, i) => (
            <View key={it.title} style={[s.source, i < SOURCES.length - 1 && s.divider]}>
              <View style={s.bubble}><Icon name={it.icon} size={17} color={c.primary} /></View>
              <View style={{ flex: 1 }}>
                <Text style={s.sourceTitle}>{it.title}</Text>
                <Text style={s.sourceText}>{it.text}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={s.warn}>
          <Icon name="alert" size={18} color="#8A5A00" />
          <Text style={s.warnText}>NATIA no está avalada por FECNA ni sustituye los resultados oficiales. Para cualquier efecto oficial, consulta a FECNA.</Text>
        </View>

        <Text style={s.h}>AYUDA Y LEGAL</Text>
        <View style={[s.card, { paddingVertical: 0 }]}>
          <Pressable style={[s.line, s.divider]} accessibilityRole="link" onPress={() => router.push('/terminos')}>
            <Text style={s.text}>Términos y condiciones</Text><Icon name="chevron" size={18} />
          </Pressable>
          <Pressable style={[s.line, s.divider]} accessibilityRole="link" onPress={() => router.push({ pathname: '/terminos', params: { seccion: '6' } })}>
            <Text style={s.text}>Tratamiento de datos · Ley 1581</Text><Icon name="chevron" size={18} />
          </Pressable>
          <Pressable style={[s.line, s.divider, { minHeight: 56 }]} accessibilityRole="link" accessibilityLabel={`Escribir a soporte, ${CONTACT_EMAIL}`} onPress={mail}>
            <View>
              <Text style={s.text}>Escribir a soporte</Text>
              <Text style={s.mail} selectable>{CONTACT_EMAIL}</Text>
            </View>
            <Icon name="mail" size={18} />
          </Pressable>
          <Pressable style={s.line} accessibilityRole="link" onPress={() => router.push('/licencias')}>
            <Text style={s.text}>Licencias de código abierto</Text><Icon name="chevron" size={18} />
          </Pressable>
        </View>

        <Text style={s.footer}>© {new Date().getFullYear()} NATIA · co.natia.app</Text>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  hero: { alignItems: 'center', gap: 6 },
  logo: { width: 72, height: 72, borderRadius: 18 },
  name: { fontFamily: font.title, fontSize: 26, color: c.deep, marginTop: 4 },
  tagline: { fontFamily: font.semi, fontSize: 14, color: c.primary },
  desc: { fontFamily: font.body, fontSize: 13, lineHeight: 19, color: c.muted, textAlign: 'center', maxWidth: 310 },
  pills: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginTop: 4 },
  pill: { backgroundColor: c.chip, color: c.deep, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 5, fontFamily: font.semi, fontSize: 11, overflow: 'hidden' },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted, marginTop: 2 },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, paddingHorizontal: 14 },
  divider: { borderBottomWidth: 1, borderBottomColor: '#E3EDF3' },
  source: { flexDirection: 'row', gap: 12, paddingVertical: 10 },
  bubble: { width: 32, height: 32, borderRadius: 16, backgroundColor: c.chip, alignItems: 'center', justifyContent: 'center' },
  sourceTitle: { fontFamily: font.semi, fontSize: 13, color: c.text },
  sourceText: { fontFamily: font.body, fontSize: 12, lineHeight: 17, color: c.muted, marginTop: 2 },
  warn: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', backgroundColor: '#FFF6E5', borderWidth: 1, borderColor: '#F2D9A6', borderRadius: 14, padding: 12 },
  warnText: { flex: 1, fontFamily: font.body, fontSize: 12, lineHeight: 17, color: '#5C3D00' },
  line: { minHeight: 48, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  text: { fontFamily: font.body, fontSize: 14, color: c.text },
  mail: { fontFamily: font.semi, fontSize: 12, color: c.primary, marginTop: 1 },
  footer: { fontFamily: font.body, fontSize: 11, color: c.muted, textAlign: 'center', marginTop: 8, marginBottom: 12 },
});
