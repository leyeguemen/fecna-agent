import { router } from 'expo-router';
import { Pressable } from 'react-native';
import { useAuth } from './auth';
import { Avatar } from './ui';

export function ProfileButton() {
  const { user } = useAuth();
  return (
    <Pressable accessibilityLabel="Mi perfil" onPress={() => router.push('/perfil')}>
      <Avatar label={user?.email ?? '?'} />
    </Pressable>
  );
}
