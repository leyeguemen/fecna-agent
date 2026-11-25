import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Header, Icon } from '../../ui';

// Menú de administración: cada opción aparece solo si el rol tiene el permiso que la habilita.
const OPTIONS = [
  { path: '/seguridad', perm: 'gestionar_usuarios', icon: 'shield', label: 'Seguridad', note: 'Usuarios, roles y permisos' },
  { path: '/sincronizar', perm: 'sincronizar', icon: 'sync', label: 'Sincronizar ranking', note: 'Datos de FECNA' },
  { path: '/programa', perm: 'cargar_programa', icon: 'upload', label: 'Cargar programa', note: 'Torneos' },
  { path: '/historial', perm: 'sincronizar', icon: 'history', label: 'Historial de un nadador', note: 'Bajo demanda' },
  { path: '/cargar-minimas', perm: 'cargar_minimas', icon: 'target', label: 'Cargar marcas mínimas', note: 'Reglamento 2026' },
];

export default function Config() {
  const { can } = useAuth();
  const items = OPTIONS.filter((o) => can(o.perm));
  return (
    <View style={s.root}>
      <Header title="Configuración" subtitle="Administración de NATIA" right={<ProfileButton />}
        onBack={() => (router.canGoBack() ? router.back() : router.replace('/perfil'))} />
      <ScrollView contentContainerStyle={{ padding: 16, paddingTop: 28 }}>
        <View style={s.grid}>
          {items.map((o) => (
            <Pressable key={o.path} accessibilityRole="button" accessibilityLabel={o.label} onPress={() => router.push(o.path as any)} style={s.cell}>
              <View style={s.circle}><Icon name={o.icon} size={32} color={c.primary} /></View>
              <Text style={s.label}>{o.label}</Text>
              <Text style={s.note}>{o.note}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: 26 },
  cell: { width: '33.33%', alignItems: 'center', paddingHorizontal: 4 },
  circle: { width: 80, height: 80, borderRadius: 40, backgroundColor: c.white, borderWidth: 1, borderColor: c.border, alignItems: 'center', justifyContent: 'center' },
  label: { fontFamily: font.semi, fontSize: 13, color: c.text, textAlign: 'center', marginTop: 10 },
  note: { fontFamily: font.body, fontSize: 11, color: c.primary, textAlign: 'center', marginTop: 2 },
});
