# iOS App Architecture

**Platform:** Pocket Radar (iOS Native)  
**Framework:** React Native + Expo  
**Version:** 1.0

---

## Overview

The iOS app is the "Pocket Radar"—optimized for push notifications (Signal Alerts), quick-glance telemetry, and mobile-native consumption of Intelligence Briefings. Built with React Native and Expo for rapid development with native performance.

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | React Native | 0.73+ |
| Platform | Expo (Managed) | SDK 50+ |
| Navigation | Expo Router | 3.x |
| State | Zustand + TanStack Query | 4.x / 5.x |
| Styling | NativeWind (Tailwind) | 4.x |
| Auth | Supabase Auth | Latest |
| Push | Expo Notifications + APNs | Latest |
| 3D (simplified) | Expo GL / Three.js | Optional |

---

## Project Structure

```
short-gravity-ios/
├── app/
│   ├── (tabs)/
│   │   ├── _layout.tsx             # Tab navigator
│   │   ├── index.tsx               # Signal Feed (Home)
│   │   ├── cockpit.tsx             # Simplified orbital view
│   │   ├── briefings.tsx           # Briefing list
│   │   └── profile.tsx             # Settings/Profile
│   │
│   ├── (auth)/
│   │   ├── _layout.tsx
│   │   ├── login.tsx
│   │   └── signup.tsx
│   │
│   ├── signal/
│   │   └── [id].tsx                # Signal detail
│   │
│   ├── briefing/
│   │   └── [id].tsx                # Briefing reader
│   │
│   ├── entity/
│   │   └── [slug].tsx              # Entity detail
│   │
│   ├── _layout.tsx                 # Root layout
│   └── +not-found.tsx
│
├── components/
│   ├── ui/                         # Base components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   └── Badge.tsx
│   │
│   ├── signals/
│   │   ├── SignalCard.tsx
│   │   ├── SignalList.tsx
│   │   └── SignalFilters.tsx
│   │
│   ├── briefings/
│   │   ├── BriefingCard.tsx
│   │   └── BriefingReader.tsx
│   │
│   ├── cockpit/
│   │   ├── MiniCockpit.tsx         # Simplified 2D/3D view
│   │   ├── SatelliteRow.tsx
│   │   └── TelemetryCard.tsx
│   │
│   └── common/
│       ├── Header.tsx
│       ├── EmptyState.tsx
│       └── LoadingSpinner.tsx
│
├── lib/
│   ├── supabase.ts                 # Supabase client
│   ├── notifications.ts            # Push notification setup
│   ├── api/
│   │   ├── signals.ts
│   │   ├── briefings.ts
│   │   ├── watchlist.ts
│   │   └── orbital.ts
│   └── utils/
│       ├── formatting.ts
│       └── storage.ts
│
├── hooks/
│   ├── useSignals.ts
│   ├── useBriefings.ts
│   ├── useWatchlist.ts
│   ├── usePushNotifications.ts
│   └── useAuth.ts
│
├── stores/
│   ├── auth.ts
│   └── notifications.ts
│
├── types/
│   └── index.ts
│
├── assets/
│   ├── images/
│   └── fonts/
│
├── app.json                        # Expo config
├── babel.config.js
├── tailwind.config.js
├── tsconfig.json
├── eas.json                        # EAS Build config
└── package.json
```

---

## Key Screens

### Signal Feed (Home Tab)

```tsx
// app/(tabs)/index.tsx
import { View, FlatList, RefreshControl } from 'react-native';
import { useSignals } from '@/hooks/useSignals';
import { SignalCard } from '@/components/signals/SignalCard';
import { SignalFilters } from '@/components/signals/SignalFilters';

export default function SignalFeedScreen() {
  const { data: signals, isLoading, refetch, isRefetching } = useSignals();
  const [filters, setFilters] = useState({ severity: 'all', type: 'all' });
  
  const filteredSignals = useMemo(() => {
    return signals?.filter(s => {
      if (filters.severity !== 'all' && s.severity !== filters.severity) return false;
      if (filters.type !== 'all' && s.anomaly_type !== filters.type) return false;
      return true;
    });
  }, [signals, filters]);
  
  return (
    <View className="flex-1 bg-gray-950">
      <SignalFilters filters={filters} onChange={setFilters} />
      
      <FlatList
        data={filteredSignals}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <SignalCard signal={item} />
        )}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} />
        }
        contentContainerStyle={{ padding: 16, gap: 12 }}
      />
    </View>
  );
}
```

### Briefing Reader

```tsx
// app/briefing/[id].tsx
import { View, ScrollView, Text } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useBriefing } from '@/hooks/useBriefings';
import { Markdown } from '@/components/ui/Markdown';
import { RelatedSignal } from '@/components/briefings/RelatedSignal';

export default function BriefingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: briefing, isLoading } = useBriefing(id);
  
  if (isLoading) return <LoadingSpinner />;
  if (!briefing) return <NotFound />;
  
  return (
    <ScrollView className="flex-1 bg-gray-950 p-4">
      {/* Header */}
      <View className="mb-4">
        <Text className="text-xs text-gray-500 uppercase tracking-wider">
          {briefing.type} briefing
        </Text>
        <Text className="text-xl font-semibold text-white mt-1">
          {briefing.title || 'Intelligence Briefing'}
        </Text>
        <Text className="text-sm text-gray-400 mt-1">
          {formatDate(briefing.created_at)}
        </Text>
      </View>
      
      {/* Content */}
      <Markdown content={briefing.content} />
      
      {/* Related Signal */}
      {briefing.signal_id && (
        <RelatedSignal signalId={briefing.signal_id} />
      )}
    </ScrollView>
  );
}
```

### Mini Cockpit

A simplified orbital view optimized for mobile—2D ground track or simplified 3D.

```tsx
// components/cockpit/MiniCockpit.tsx
import { View, Dimensions } from 'react-native';
import Svg, { Circle, Path, Image as SvgImage } from 'react-native-svg';
import { useCockpitPositions } from '@/hooks/useCockpitPositions';

const { width } = Dimensions.get('window');
const MAP_WIDTH = width - 32;
const MAP_HEIGHT = MAP_WIDTH * 0.5; // 2:1 aspect ratio

export function MiniCockpit({ watchlistIds }: { watchlistIds: string[] }) {
  const { data: positions } = useCockpitPositions(watchlistIds);
  
  // Convert geodetic to SVG coordinates
  const toSvg = (lat: number, lon: number) => ({
    x: ((lon + 180) / 360) * MAP_WIDTH,
    y: ((90 - lat) / 180) * MAP_HEIGHT,
  });
  
  return (
    <View className="bg-gray-900 rounded-xl overflow-hidden">
      <Svg width={MAP_WIDTH} height={MAP_HEIGHT}>
        {/* World map background */}
        <SvgImage
          href={require('@/assets/images/world-map.png')}
          width={MAP_WIDTH}
          height={MAP_HEIGHT}
        />
        
        {/* Satellite markers */}
        {positions?.map((sat) => {
          const pos = toSvg(sat.geodetic.latitude, sat.geodetic.longitude);
          return (
            <Circle
              key={sat.id}
              cx={pos.x}
              cy={pos.y}
              r={4}
              fill={sat.anomaly ? '#ef4444' : '#22c55e'}
            />
          );
        })}
      </Svg>
    </View>
  );
}
```

---

## Push Notifications

### Setup

```typescript
// lib/notifications.ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { supabase } from './supabase';

// Configure notification behavior
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    console.log('Push notifications require a physical device');
    return null;
  }
  
  // Check permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;
  
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  
  if (finalStatus !== 'granted') {
    console.log('Push notification permission denied');
    return null;
  }
  
  // Get Expo push token
  const { data: token } = await Notifications.getExpoPushTokenAsync({
    projectId: 'your-expo-project-id',
  });
  
  // Register with backend
  await supabase.functions.invoke('register-push-token', {
    body: { token: token, platform: 'ios' },
  });
  
  return token;
}
```

### Hook

```typescript
// hooks/usePushNotifications.ts
import { useEffect, useRef, useState } from 'react';
import * as Notifications from 'expo-notifications';
import { useRouter } from 'expo-router';
import { registerForPushNotifications } from '@/lib/notifications';

export function usePushNotifications() {
  const router = useRouter();
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const notificationListener = useRef<Notifications.Subscription>();
  const responseListener = useRef<Notifications.Subscription>();
  
  useEffect(() => {
    // Register for push
    registerForPushNotifications().then(setExpoPushToken);
    
    // Handle notification received while app is foregrounded
    notificationListener.current = Notifications.addNotificationReceivedListener(
      (notification) => {
        // Could show in-app toast
        console.log('Notification received:', notification);
      }
    );
    
    // Handle notification tap
    responseListener.current = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        const data = response.notification.request.content.data;
        
        // Navigate based on notification type
        if (data.signal_id) {
          router.push(`/signal/${data.signal_id}`);
        } else if (data.briefing_id) {
          router.push(`/briefing/${data.briefing_id}`);
        }
      }
    );
    
    return () => {
      if (notificationListener.current) {
        Notifications.removeNotificationSubscription(notificationListener.current);
      }
      if (responseListener.current) {
        Notifications.removeNotificationSubscription(responseListener.current);
      }
    };
  }, [router]);
  
  return { expoPushToken };
}
```

### Notification Payload

From the backend Edge Function:

```typescript
// Example push notification payload
{
  to: 'ExponentPushToken[xxxxx]',
  title: '🚨 High Signal: STARLINK-1234',
  body: 'Orbital deviation detected. 2.3σ from baseline.',
  data: {
    signal_id: 'uuid',
    entity_slug: 'starlink-1234',
  },
  badge: 5,
  sound: 'default',
}
```

---

## Authentication

```typescript
// hooks/useAuth.ts
import { useEffect, useState } from 'react';
import { useRouter, useSegments } from 'expo-router';
import { Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const segments = useSegments();
  
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setIsLoading(false);
    });
    
    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
      }
    );
    
    return () => subscription.unsubscribe();
  }, []);
  
  // Protect routes
  useEffect(() => {
    if (isLoading) return;
    
    const inAuthGroup = segments[0] === '(auth)';
    
    if (!session && !inAuthGroup) {
      // Redirect to login
      router.replace('/login');
    } else if (session && inAuthGroup) {
      // Redirect to home
      router.replace('/');
    }
  }, [session, segments, isLoading]);
  
  return { session, isLoading };
}
```

---

## Offline Support

### Async Storage for Cached Data

```typescript
// lib/utils/storage.ts
import AsyncStorage from '@react-native-async-storage/async-storage';

export const storage = {
  async get<T>(key: string): Promise<T | null> {
    const value = await AsyncStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  },
  
  async set<T>(key: string, value: T): Promise<void> {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  },
  
  async remove(key: string): Promise<void> {
    await AsyncStorage.removeItem(key);
  },
};
```

### TanStack Query Persistence

```typescript
// app/_layout.tsx
import { QueryClient } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import AsyncStorage from '@react-native-async-storage/async-storage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 1000 * 60 * 60 * 24, // 24 hours
    },
  },
});

const asyncStoragePersister = createAsyncStoragePersister({
  storage: AsyncStorage,
});

export default function RootLayout() {
  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister: asyncStoragePersister }}
    >
      {/* ... */}
    </PersistQueryClientProvider>
  );
}
```

---

## Navigation Structure

```
Tab Navigator (tabs)
├── Signal Feed (index) ─────────────────┐
│                                        │
├── Cockpit (cockpit)                    │
│                                        ├─→ Signal Detail (/signal/[id])
├── Briefings (briefings) ───────────────┼─→ Briefing Reader (/briefing/[id])
│                                        │
└── Profile (profile)                    └─→ Entity Detail (/entity/[slug])
```

```tsx
// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router';
import { Home, Radar, FileText, User } from 'lucide-react-native';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#22c55e',
        tabBarInactiveTintColor: '#6b7280',
        tabBarStyle: {
          backgroundColor: '#111827',
          borderTopColor: '#1f2937',
        },
        headerStyle: { backgroundColor: '#111827' },
        headerTintColor: '#fff',
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Signals',
          tabBarIcon: ({ color }) => <Home size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="cockpit"
        options={{
          title: 'Cockpit',
          tabBarIcon: ({ color }) => <Radar size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="briefings"
        options={{
          title: 'Briefings',
          tabBarIcon: ({ color }) => <FileText size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <User size={24} color={color} />,
        }}
      />
    </Tabs>
  );
}
```

---

## App Configuration

```json
// app.json
{
  "expo": {
    "name": "Short Gravity",
    "slug": "short-gravity",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "userInterfaceStyle": "dark",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#030712"
    },
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.shortgravity.app",
      "buildNumber": "1",
      "infoPlist": {
        "UIBackgroundModes": ["remote-notification"]
      }
    },
    "plugins": [
      "expo-router",
      [
        "expo-notifications",
        {
          "icon": "./assets/notification-icon.png",
          "color": "#22c55e"
        }
      ]
    ],
    "extra": {
      "eas": {
        "projectId": "your-project-id"
      }
    }
  }
}
```

---

## EAS Build Configuration

```json
// eas.json
{
  "cli": {
    "version": ">= 5.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": {
        "simulator": true
      }
    },
    "preview": {
      "distribution": "internal",
      "ios": {
        "resourceClass": "m-medium"
      }
    },
    "production": {
      "ios": {
        "resourceClass": "m-medium"
      }
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your@email.com",
        "ascAppId": "your-app-store-connect-app-id"
      }
    }
  }
}
```

---

## Environment Variables

```env
# .env
EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Performance Optimization

1. **List Rendering**
   - Use `FlatList` with `getItemLayout` for fixed-height items
   - Implement `windowSize` and `maxToRenderPerBatch`

2. **Images**
   - Use `expo-image` for caching and performance
   - Serve appropriately sized images

3. **Navigation**
   - Lazy load screens with `React.lazy`
   - Use `expo-router`'s built-in code splitting

4. **Memory**
   - Clean up subscriptions in `useEffect` cleanup
   - Limit real-time subscriptions to visible content
