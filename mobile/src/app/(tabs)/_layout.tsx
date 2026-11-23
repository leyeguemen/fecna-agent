import { Redirect, Tabs, usePathname } from 'expo-router';
import { Platform } from 'react-native';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { Empty, Icon } from '../../ui';
import { webSafeBottom } from '../../webInsets';

const tab = (title: string, icon: string) => ({
  title,
  tabBarIcon: ({ color }: { color: unknown }) => <Icon name={icon} color={String(color)} />,
});

// Pestaña → permiso que la habilita (en orden de preferencia para la pantalla inicial).
const SCREENS = [
  { path: '/', perms: ['chat'] },
  { path: '/ranking', perms: ['ver_ranking'] },
  { path: '/nadador', perms: ['ver_nadador'] },
  { path: '/torneos', perms: ['ver_torneos'] },
  { path: '/minimas', perms: ['ver_minimas'] },
  { path: '/config', perms: ['sincronizar', 'cargar_programa', 'gestionar_usuarios', 'cargar_minimas'] },
  { path: '/cargar-minimas', perms: ['cargar_minimas'] },
  { path: '/seguridad', perms: ['gestionar_usuarios'] },
  { path: '/sincronizar', perms: ['sincronizar'] },
  { path: '/programa', perms: ['cargar_programa'] },
  { path: '/historial', perms: ['sincronizar'] },
];
// Una pestaña oculta con display:none sigue siendo una ruta válida (href:null la elimina).
const hidden = { tabBarItemStyle: { display: 'none' as const } };

export default function TabsLayout() {
  const { can, pendingLink } = useAuth();
  const pathname = usePathname();
  const allowed = (perms: string[]) => perms.some(can);
  const isAdmin = allowed(['sincronizar', 'cargar_programa', 'gestionar_usuarios', 'cargar_minimas']);
  if (pendingLink) return <Redirect href="/vincular?first=1" />;
  // Si la pantalla actual ya no está permitida (o el rol cambió), ir a la primera que sí lo esté.
  const here = SCREENS.find((sc) => sc.path === pathname);
  if (here && !allowed(here.perms)) {
    const first = SCREENS.find((sc) => allowed(sc.perms));
    if (first) return <Redirect href={first.path as any} />;
    return <Empty text="Tu cuenta no tiene opciones habilitadas por ahora. Pide acceso al administrador." />;
  }
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarHideOnKeyboard: true, // deja sitio a la caja de texto cuando aparece el teclado
      tabBarActiveTintColor: c.primary,
      tabBarInactiveTintColor: c.muted,
      tabBarLabelStyle: { fontFamily: font.semi, fontSize: 11 },
      // En web la altura por defecto recorta las etiquetas: se da espacio explícito.
      tabBarStyle: { backgroundColor: c.white, borderTopColor: c.border, ...(Platform.OS === 'web' ? { height: 66 + webSafeBottom(), paddingTop: 6, paddingBottom: 8 + webSafeBottom() } : {}) },
    }}>
      <Tabs.Screen name="index" options={{ ...tab('Chat', 'chat'), ...(can('chat') ? {} : hidden) }} />
      <Tabs.Screen name="ranking" options={{ ...tab('Ranking', 'ranking'), ...(can('ver_ranking') ? {} : hidden) }} />
      <Tabs.Screen name="nadador" options={{ ...tab('Nadador', 'swimmer'), ...(can('ver_nadador') ? {} : hidden) }} />
      <Tabs.Screen name="torneos" options={{ ...tab('Torneos', 'calendar'), ...(can('ver_torneos') ? {} : hidden) }} />
      <Tabs.Screen name="minimas" options={{ ...tab('Mínimas', 'target'), ...(can('ver_minimas') ? {} : hidden) }} />
      {/* Configuración: una sola pestaña para lo administrativo; solo con algún permiso de administración. */}
      <Tabs.Screen name="config" options={{ ...tab('Config', 'gear'), href: isAdmin ? undefined : null }} />
      {/* Sub-pantallas de Configuración: rutas válidas, fuera de la barra (el backend igual valida cada permiso). */}
      <Tabs.Screen name="seguridad" options={hidden} />
      <Tabs.Screen name="sincronizar" options={hidden} />
      <Tabs.Screen name="programa" options={hidden} />
      <Tabs.Screen name="historial" options={hidden} />
      <Tabs.Screen name="cargar-minimas" options={hidden} />
      {/* Perfil se abre desde el avatar: se oculta de la barra, pero sigue siendo navegable (href: null la sacaba de las rutas). */}
      <Tabs.Screen name="perfil" options={{ tabBarItemStyle: { display: 'none' } }} />
    </Tabs>
  );
}
