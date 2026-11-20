import { ReactNode } from 'react';
import {
  ActivityIndicator, Modal, Pressable, StyleSheet, Text, TextInput, TextInputProps, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path, Circle, Rect } from 'react-native-svg';
import { c, font } from './theme';

// ---- Iconos (trazos del diseño) ------------------------------------------------
const ICONS: Record<string, ReactNode> = {
  chat: <Path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  ranking: <Path d="M8 21V10M16 21V4M12 21v-7M3 21h18" />,
  swimmer: <><Circle cx="12" cy="8" r="4" /><Path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></>,
  calendar: <><Rect x="3" y="4" width="18" height="18" rx="2" /><Path d="M16 2v4M8 2v4M3 10h18" /></>,
  sync: <><Path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><Path d="M21 3v5h-5" /></>,
  send: <><Path d="M22 2L11 13" /><Path d="M22 2l-7 20-4-9-9-4 20-7z" /></>,
  logout: <><Path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><Path d="M16 17l5-5-5-5" /><Path d="M21 12H9" /></>,
  chevron: <Path d="M9 18l6-6-6-6" />,
  upload: <><Path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><Path d="M17 8l-5-5-5 5" /><Path d="M12 3v12" /></>,
};

export function Icon({ name, size = 22, color = c.muted }: { name: keyof typeof ICONS | string; size?: number; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {ICONS[name]}
    </Svg>
  );
}

// ---- Piezas ---------------------------------------------------------------------
export const initials = (s: string) =>
  s.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');

export function Avatar({ label, size = 36 }: { label: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: c.accent, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: c.deep, fontFamily: font.semi, fontSize: size * 0.36 }}>{initials(label)}</Text>
    </View>
  );
}

export function Header({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[s.header, { paddingTop: insets.top + 12 }]}>
      <View style={{ flex: 1 }}>
        <Text style={s.headerTitle}>{title}</Text>
        {subtitle ? <Text style={s.headerSub}>{subtitle}</Text> : null}
      </View>
      {right}
    </View>
  );
}

export function Button({ title, onPress, variant = 'primary', disabled, loading }: {
  title: string; onPress: () => void; variant?: 'primary' | 'outline' | 'danger'; disabled?: boolean; loading?: boolean;
}) {
  const bg = variant === 'primary' ? c.primary : variant === 'danger' ? c.danger : c.white;
  const fg = variant === 'outline' ? c.deep : c.white;
  return (
    <Pressable accessibilityRole="button" onPress={onPress} disabled={disabled || loading}
      style={[s.btn, { backgroundColor: bg, borderWidth: variant === 'outline' ? 1.5 : 0, borderColor: c.deep, opacity: disabled ? 0.5 : 1 }]}>
      {loading ? <ActivityIndicator color={fg} /> : <Text style={[s.btnText, { color: fg }]}>{title}</Text>}
    </Pressable>
  );
}

export function Field({ label, ...props }: { label: string } & TextInputProps) {
  return (
    <View>
      <Text style={s.label}>{label}</Text>
      <TextInput placeholderTextColor="#8AA3B5" autoCapitalize="none" style={s.input} {...props} />
    </View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected?: boolean; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={[s.chip, selected && { backgroundColor: c.primary }]}>
      <Text style={[s.chipText, selected && { color: c.white }]}>{label}</Text>
    </Pressable>
  );
}

export const Card = ({ children }: { children: ReactNode }) => <View style={s.card}>{children}</View>;

export const Empty = ({ text }: { text: string }) => (
  <Text style={{ textAlign: 'center', color: c.muted, fontFamily: font.body, marginTop: 32 }}>{text}</Text>
);

export const ErrorText = ({ text }: { text: string | null }) =>
  text ? <Text style={{ color: c.danger, fontFamily: font.body, fontSize: 13 }}>{text}</Text> : null;

/** Diálogo de confirmación (diseño "Diálogos"). */
export function ConfirmDialog({ visible, title, message, confirmLabel, danger, confirmDisabled, onConfirm, onCancel, children }: {
  visible: boolean; title: string; message: string; confirmLabel: string; danger?: boolean; confirmDisabled?: boolean;
  onConfirm: () => void; onCancel: () => void; children?: ReactNode;
}) {
  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onCancel}>
      <View style={s.overlay}>
        <View style={s.dialog} accessibilityRole="alert">
          <Text style={s.dialogTitle}>{title}</Text>
          <Text style={s.dialogMsg}>{message}</Text>
          {children}
          <View style={{ flexDirection: 'row', gap: 10, marginTop: 20 }}>
            <View style={{ flex: 1 }}><Button title="Cancelar" variant="outline" onPress={onCancel} /></View>
            <View style={{ flex: 1 }}><Button title={confirmLabel} variant={danger ? 'danger' : 'primary'} onPress={onConfirm} disabled={confirmDisabled} /></View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  header: { backgroundColor: c.deep, paddingHorizontal: 20, paddingVertical: 16, flexDirection: 'row', alignItems: 'center' },
  headerTitle: { color: c.white, fontFamily: font.title, fontSize: 20 },
  headerSub: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  btn: { height: 50, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 },
  btnText: { fontFamily: font.bold, fontSize: 15 },
  label: { fontFamily: font.medium, fontSize: 12, color: c.muted },
  input: { height: 52, marginTop: 6, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 16, fontSize: 15, fontFamily: font.body, color: c.text, backgroundColor: c.white },
  chip: { backgroundColor: c.chip, borderRadius: 16, paddingHorizontal: 12, paddingVertical: 8 },
  chipText: { color: c.deep, fontFamily: font.medium, fontSize: 12 },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, padding: 14 },
  overlay: { flex: 1, backgroundColor: 'rgba(2,30,70,.55)', alignItems: 'center', justifyContent: 'center', padding: 24 },
  dialog: { width: '100%', maxWidth: 340, backgroundColor: c.white, borderRadius: 20, padding: 22 },
  dialogTitle: { fontFamily: font.title, fontSize: 18, color: c.text },
  dialogMsg: { fontFamily: font.body, fontSize: 14, color: c.muted, lineHeight: 20, marginTop: 8 },
});
