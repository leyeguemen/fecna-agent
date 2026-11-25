import { router } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { LICENSES } from '../legal';
import { c, font } from '../theme';
import { Button, Card } from '../ui';

// Se abre desde Acerca de.
export default function Licencias() {
  return (
    <View style={s.root}>
      <View style={s.header}>
        <Text style={s.title}>Licencias de código abierto</Text>
        <Text style={s.sub}>NATIA se construye con estas bibliotecas y fuentes</Text>
      </View>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>
        <Card>
          {LICENSES.map((l, i) => (
            <View key={l.name} style={[s.row, i < LICENSES.length - 1 && s.divider]}>
              <Text style={s.name}>{l.name}</Text>
              <Text style={s.license}>{l.license}</Text>
            </View>
          ))}
        </Card>
        <Text style={s.note}>Gracias a quienes mantienen estos proyectos.</Text>
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
  row: { paddingVertical: 10, gap: 2 },
  divider: { borderBottomWidth: 1, borderBottomColor: c.border },
  name: { fontFamily: font.semi, fontSize: 14, color: c.text },
  license: { fontFamily: font.body, fontSize: 12, color: c.muted },
  note: { fontFamily: font.body, fontSize: 12, color: c.muted, textAlign: 'center' },
});
