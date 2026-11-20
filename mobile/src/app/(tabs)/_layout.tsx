import { Tabs } from 'expo-router';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { Icon } from '../../ui';

const tab = (title: string, icon: string) => ({
  title,
  tabBarIcon: ({ color }: { color: unknown }) => <Icon name={icon} color={String(color)} />,
});

export default function TabsLayout() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: c.primary,
      tabBarInactiveTintColor: c.muted,
      tabBarLabelStyle: { fontFamily: font.semi, fontSize: 11 },
      tabBarStyle: { backgroundColor: c.white, borderTopColor: c.border },
    }}>
      <Tabs.Screen name="index" options={tab('Chat', 'chat')} />
      <Tabs.Screen name="ranking" options={tab('Ranking', 'ranking')} />
      <Tabs.Screen name="nadador" options={tab('Nadador', 'swimmer')} />
      <Tabs.Screen name="torneos" options={tab('Torneos', 'calendar')} />
      {/* Admin solo visible con rol admin (el backend igual responde 403 a los demás). */}
      <Tabs.Screen name="admin" options={{ ...tab('Admin', 'sync'), href: isAdmin ? undefined : null }} />
      <Tabs.Screen name="perfil" options={{ href: null }} />
    </Tabs>
  );
}
