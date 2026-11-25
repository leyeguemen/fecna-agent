import { router, useLocalSearchParams } from 'expo-router';
import { useRef } from 'react';
import { ScrollView, ScrollViewInstance, StyleSheet, Text, View } from 'react-native';
import { SOURCE_NOTE, TERMS, TERMS_VERSION } from '../legal';
import { c, font } from '../theme';
import { Button } from '../ui';

// Se puede abrir con o sin sesión (desde Login, Registro, Perfil y Acerca de).
// `seccion` (p. ej. "6") lleva directo a esa sección: Acerca de → Tratamiento de datos.
export default function Terminos() {
  const { seccion } = useLocalSearchParams<{ seccion?: string }>();
  const scroll = useRef<ScrollViewInstance>(null);
  const target = seccion ? TERMS.findIndex((t) => t.title.startsWith(`${seccion}.`)) : -1;
  // Solo el primer layout: si luego cambia (giro, fuentes), no se le quita el lugar a quien ya se desplazó.
  const jumped = useRef(false);
  const jumpTo = (y: number) => {
    if (jumped.current) return;
    jumped.current = true;
    scroll.current?.scrollTo({ y: Math.max(0, y - 12), animated: false });
  };

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Text style={s.title}>Términos y condiciones</Text>
        <Text style={s.sub}>NATIA — Tu asistente de natación</Text>
      </View>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 20, gap: 14 }}>
        <View style={s.note}><Text style={s.noteText}>{SOURCE_NOTE}</Text></View>
        {TERMS.map((t, i) => (
          <View key={t.title} style={{ gap: 4 }}
            onLayout={i === target ? (e) => jumpTo(e.nativeEvent.layout.y) : undefined}>
            <Text style={s.h}>{t.title}</Text>
            <Text style={s.p}>{t.body}</Text>
          </View>
        ))}
        <Text style={s.version}>Versión {TERMS_VERSION}</Text>
        <Button title="Cerrar" variant="outline" onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} />
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, paddingHorizontal: 20, paddingTop: 56, paddingBottom: 16 },
  title: { color: c.white, fontFamily: font.title, fontSize: 22 },
  sub: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  note: { backgroundColor: c.chip, borderColor: c.accent, borderWidth: 1, borderRadius: 12, padding: 12 },
  noteText: { color: c.deep, fontFamily: font.semi, fontSize: 13, lineHeight: 19 },
  h: { fontFamily: font.bold, fontSize: 14, color: c.text },
  p: { fontFamily: font.body, fontSize: 13, color: c.muted, lineHeight: 20 },
  version: { fontFamily: font.body, fontSize: 11, color: c.muted, textAlign: 'center', marginTop: 4 },
});
