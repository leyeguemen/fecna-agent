import { Redirect, Tabs } from 'expo-router';
import { Platform } from 'react-native';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { Icon } from '../../ui';
import { webSafeBottom } from '../../webInsets';

const tab = (title: string, icon: string) => ({
  title,
  tabBarIcon: ({ color }: { color: unknown }) => <Icon name={icon} color={String(color)} />,
});

export default function TabsLayout() {
  const { user, pendingLink } = useAuth();
  const isAdmin = user?.role === 'admin';
  if (pendingLink) return <Redirect href="/vincular?first=1" />;
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: c.primary,
      tabBarInactiveTintColor: c.muted,
      tabBarLabelStyle: { fontFamily: font.semi, fontSize: 11 },
      // En web la altura por defecto recorta las etiquetas: se da espacio explícito.
      tabBarStyle: { backgroundColor: c.white, borderTopColor: c.border, ...(Platform.OS === 'web' ? { height: 66 + webSafeBottom(), paddingTop: 6, paddingBottom: 8 + webSafeBottom() } : {}) },
    }}>
      <Tabs.Screen name="index" options={tab('Chat', 'chat')} />
      <Tabs.Screen name="ranking" options={tab('Ranking', 'ranking')} />
      <Tabs.Screen name="nadador" options={tab('Nadador', 'swimmer')} />
      <Tabs.Screen name="torneos" options={tab('Torneos', 'calendar')} />
      {/* Admin solo visible con rol admin (el backend igual responde 403 a los demás). */}
      <Tabs.Screen name="admin" options={{ ...tab('Admin', 'sync'), href: isAdmin ? undefined : null }} />
      {/* Perfil se abre desde el avatar: se oculta de la barra, pero sigue siendo navegable (href: null la sacaba de las rutas). */}
      <Tabs.Screen name="perfil" options={{ tabBarItemStyle: { display: 'none' } }} />
    </Tabs>
  );
}
