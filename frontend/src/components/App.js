// App.js - Main Mobile App for Diriyah Brain AI
import React, { useState, useEffect, useRef } from 'react';
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Image,
  StyleSheet,
  StatusBar,
  Alert,
  Platform,
  ActivityIndicator,
  RefreshControl,
  Modal
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import NetInfo from '@react-native-community/netinfo';

// =====================================================
// CONFIGURATION & CONSTANTS
// =====================================================

const API_BASE_URL = 'https://api.diriyah-brain.ai';
const WS_URL = 'wss://api.diriyah-brain.ai/ws';

const COLORS = {
  primary: '#D97706',
  secondary: '#92400E',
  accent: '#FBBF24',
  background: '#FFFBEB',
  card: '#FFFFFF',
  text: '#1F2937',
  textLight: '#6B7280',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  border: '#E5E7EB'
};

// =====================================================
// MOBILE APP COMPONENT
// =====================================================

const DiriyahMobileApp = () => {
  // State Management
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [currentScreen, setCurrentScreen] = useState('home');
  const [isOnline, setIsOnline] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [photoDescription, setPhotoDescription] = useState('');

  // Data State
  const [projects, setProjects] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [tasks, setTasks] = useState([]);

  // Chat State
  const [messageInput, setMessageInput] = useState('');
  const [isAITyping, setIsAITyping] = useState(false);

  // Modal State
  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  // Refs
  const wsRef = useRef(null);
  const chatScrollRef = useRef(null);
  const notificationListenerRef = useRef(null);
  const netinfoUnsubscribeRef = useRef(null);

  // =====================================================
  // INITIALIZATION & LIFECYCLE
  // =====================================================

  useEffect(() => {
    initializeApp();
    setupNotifications();
    netinfoUnsubscribeRef.current = setupNetworkListener();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (notificationListenerRef.current) {
        notificationListenerRef.current.remove();
      }
      if (netinfoUnsubscribeRef.current) {
        netinfoUnsubscribeRef.current();
      }
    };
  }, []);

  useEffect(() => {
    if (isLoggedIn && user) {
      connectWebSocket();
      loadUserData();
    }
  }, [isLoggedIn, user]);

  const initializeApp = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (userData) {
        const parsedUser = JSON.parse(userData);
        setUser(parsedUser);
        setIsLoggedIn(true);
      }

      await requestPermissions();
    } catch (error) {
      console.error('Initialization error:', error);
    }
  };

  const requestPermissions = async () => {
    const { status: locationStatus } = await Location.requestForegroundPermissionsAsync();
    if (locationStatus !== 'granted') {
      Alert.alert('Permission Required', 'Location access is needed for site monitoring.');
    }

    const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
    if (cameraStatus !== 'granted') {
      Alert.alert('Permission Required', 'Camera access is needed for photo uploads.');
    }
  };

  const setupNotifications = async () => {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Notifications are needed for alerts.');
      return;
    }

    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true
      })
    });

    notificationListenerRef.current = Notifications.addNotificationReceivedListener(notification => {
      const newAlert = {
        id: Date.now().toString(),
        title: notification.request.content.title,
        message: notification.request.content.body,
        timestamp: new Date(),
        type: 'notification'
      };
      setAlerts(prev => {
        const updatedAlerts = [newAlert, ...prev];
        AsyncStorage.setItem('alerts', JSON.stringify(updatedAlerts));
        return updatedAlerts;
      });
    });
  };

  const setupNetworkListener = () => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOnline(Boolean(state.isConnected));
      if (state.isConnected) {
        syncOfflineData();
      }
    });
    return unsubscribe;
  };

  // =====================================================
  // WEBSOCKET CONNECTION
  // =====================================================

  const connectWebSocket = () => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      wsRef.current = new WebSocket(`${WS_URL}/mobile?user_id=${user?.id}`);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = event => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      wsRef.current.onerror = error => {
        console.error('WebSocket error:', error);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setTimeout(() => {
          if (isLoggedIn && user) {
            connectWebSocket();
          }
        }, 5000);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  };

  const handleWebSocketMessage = data => {
    switch (data.type) {
      case 'alert': {
        const newAlert = {
          id: Date.now().toString(),
          ...data.payload,
          timestamp: new Date()
        };
        setAlerts(prev => {
          const updatedAlerts = [newAlert, ...prev];
          AsyncStorage.setItem('alerts', JSON.stringify(updatedAlerts));
          return updatedAlerts;
        });
        showLocalNotification(data.payload.title, data.payload.message);
        break;
      }
      case 'chat_response': {
        const aiMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.payload.message,
          timestamp: new Date()
        };
        setChatMessages(prev => {
          const updated = [...prev, aiMessage];
          AsyncStorage.setItem('chatMessages', JSON.stringify(updated));
          return updated;
        });
        setIsAITyping(false);
        break;
      }
      case 'project_update': {
        loadProjects();
        break;
      }
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const showLocalNotification = async (title, body) => {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: true
      },
      trigger: null
    });
  };

  // =====================================================
  // DATA LOADING & SYNC
  // =====================================================

  const loadUserData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([loadProjects(), loadAlerts(), loadTasks(), loadChatHistory()]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const cachedProjects = await AsyncStorage.getItem('projects');
      if (cachedProjects) {
        setProjects(JSON.parse(cachedProjects));
      }

      if (isOnline && user?.token) {
        const response = await fetch(`${API_BASE_URL}/api/projects`, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        });
        const data = await response.json();
        if (Array.isArray(data.projects)) {
          setProjects(data.projects);
          await AsyncStorage.setItem('projects', JSON.stringify(data.projects));
        }
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const loadAlerts = async () => {
    try {
      const cachedAlerts = await AsyncStorage.getItem('alerts');
      if (cachedAlerts) {
        setAlerts(JSON.parse(cachedAlerts));
      }

      if (isOnline && user?.token) {
        const response = await fetch(`${API_BASE_URL}/api/alerts`, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        });
        const data = await response.json();
        if (Array.isArray(data.alerts)) {
          setAlerts(data.alerts);
          await AsyncStorage.setItem('alerts', JSON.stringify(data.alerts));
        }
      }
    } catch (error) {
      console.error('Error loading alerts:', error);
    }
  };

  const loadTasks = async () => {
    try {
      const cachedTasks = await AsyncStorage.getItem('tasks');
      if (cachedTasks) {
        setTasks(JSON.parse(cachedTasks));
      }

      if (isOnline && user?.token) {
        const response = await fetch(`${API_BASE_URL}/api/tasks`, {
          headers: {
            Authorization: `Bearer ${user.token}`
          }
        });
        const data = await response.json();
        if (Array.isArray(data.tasks)) {
          setTasks(data.tasks);
          await AsyncStorage.setItem('tasks', JSON.stringify(data.tasks));
        }
      }
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
  };

  const loadChatHistory = async () => {
    try {
      const cachedChat = await AsyncStorage.getItem('chatMessages');
      if (cachedChat) {
        setChatMessages(JSON.parse(cachedChat));
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const syncOfflineData = async () => {
    try {
      const offlineActions = await AsyncStorage.getItem('offlineActions');
      if (offlineActions) {
        const actions = JSON.parse(offlineActions);
        for (const action of actions) {
          await processOfflineAction(action);
        }
        await AsyncStorage.removeItem('offlineActions');
      }

      const offlinePhotos = await AsyncStorage.getItem('offlinePhotos');
      if (offlinePhotos && isOnline && user?.token) {
        const photos = JSON.parse(offlinePhotos);
        for (const photo of photos) {
          await uploadPhotoFromQueue(photo);
        }
        await AsyncStorage.removeItem('offlinePhotos');
      }
    } catch (error) {
      console.error('Error syncing offline data:', error);
    }
  };

  const processOfflineAction = async action => {
    console.log('Processing offline action:', action);
  };

  const uploadPhotoFromQueue = async photo => {
    try {
      const formData = new FormData();
      formData.append('photo', {
        uri: photo.uri,
        type: 'image/jpeg',
        name: `site_photo_${Date.now()}.jpg`
      });
      formData.append('description', photo.description || '');
      formData.append('latitude', photo.location?.latitude ?? '');
      formData.append('longitude', photo.location?.longitude ?? '');
      formData.append('timestamp', photo.timestamp || new Date().toISOString());

      const response = await fetch(`${API_BASE_URL}/api/photos/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${user.token}`
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Queued upload failed');
      }
    } catch (error) {
      console.error('Queued photo upload error:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadUserData();
    setRefreshing(false);
  };

  // =====================================================
  // CHAT FUNCTIONALITY
  // =====================================================

  const sendMessage = async () => {
    if (!messageInput.trim()) {
      return;
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: messageInput,
      timestamp: new Date()
    };

    setMessageInput('');
    setIsAITyping(true);

    setChatMessages(prev => {
      const updated = [...prev, userMessage];
      AsyncStorage.setItem('chatMessages', JSON.stringify(updated));
      return updated;
    });

    if (isOnline && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'chat_message',
          payload: {
            message: userMessage.content,
            user_id: user?.id
          }
        })
      );
    } else {
      setIsAITyping(false);
      Alert.alert('Offline', 'Your message will be sent when connection is restored.');
    }
  };

  // =====================================================
  // PHOTO CAPTURE & UPLOAD
  // =====================================================

  const capturePhoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8
    });

    if (!result.canceled) {
      setSelectedPhoto(result.assets[0]);
      setPhotoDescription('');
      setShowPhotoModal(true);
    }
  };

  const uploadPhoto = async description => {
    if (!selectedPhoto) {
      return;
    }

    try {
      setIsLoading(true);
      const location = await Location.getCurrentPositionAsync({});

      const formData = new FormData();
      formData.append('photo', {
        uri: selectedPhoto.uri,
        type: 'image/jpeg',
        name: 'site_photo.jpg'
      });
      formData.append('description', description);
      formData.append('latitude', location.coords.latitude);
      formData.append('longitude', location.coords.longitude);
      formData.append('timestamp', new Date().toISOString());

      if (isOnline && user?.token) {
        const response = await fetch(`${API_BASE_URL}/api/photos/upload`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${user.token}`
          },
          body: formData
        });

        if (response.ok) {
          Alert.alert('Success', 'Photo uploaded successfully!');
          setShowPhotoModal(false);
          setSelectedPhoto(null);
          setPhotoDescription('');
        } else {
          throw new Error('Upload failed');
        }
      } else {
        const offlinePhotos = (await AsyncStorage.getItem('offlinePhotos')) || '[]';
        const photos = JSON.parse(offlinePhotos);
        photos.push({
          uri: selectedPhoto.uri,
          description,
          location: location.coords,
          timestamp: new Date().toISOString()
        });
        await AsyncStorage.setItem('offlinePhotos', JSON.stringify(photos));
        Alert.alert('Saved Offline', 'Photo will be uploaded when connection is restored.');
        setShowPhotoModal(false);
        setSelectedPhoto(null);
        setPhotoDescription('');
      }
    } catch (error) {
      console.error('Photo upload error:', error);
      Alert.alert('Error', 'Failed to upload photo');
    } finally {
      setIsLoading(false);
    }
  };

  // =====================================================
  // AUTHENTICATION
  // =====================================================

  const login = async (emailInput, passwordInput) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: emailInput, password: passwordInput })
      });

      const data = await response.json();

      if (response.ok) {
        setUser(data.user);
        await AsyncStorage.setItem('user', JSON.stringify(data.user));
        setIsLoggedIn(true);
      } else {
        Alert.alert('Login Failed', data.message || 'Invalid credentials');
      }
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert('Error', 'Failed to login');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    await AsyncStorage.clear();
    setUser(null);
    setIsLoggedIn(false);
    setEmail('');
    setPassword('');
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  // =====================================================
  // RENDER SCREENS
  // =====================================================

  const renderLoginScreen = () => (
    <View style={styles.loginContainer}>
      <View style={styles.loginCard}>
        <Text style={styles.loginTitle}>Diriyah Brain AI</Text>
        <Text style={styles.loginSubtitle}>Mobile Project Management</Text>

        <TextInput
          style={styles.input}
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />

        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={styles.loginButton}
          onPress={() => login(email, password)}
          disabled={isLoading}
        >
          {isLoading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.loginButtonText}>Login</Text>}
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderHomeScreen = () => (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Welcome back,</Text>
          <Text style={styles.headerName}>{user?.name}</Text>
        </View>
        <View style={[styles.statusBadge, isOnline ? styles.online : styles.offline]}>
          <Text style={styles.statusText}>{isOnline ? '🟢 Online' : '🔴 Offline'}</Text>
        </View>
      </View>

      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Text style={styles.statNumber}>{projects.length}</Text>
          <Text style={styles.statLabel}>Projects</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statNumber}>{alerts.length}</Text>
          <Text style={styles.statLabel}>Alerts</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statNumber}>{tasks.filter(t => !t.completed).length}</Text>
          <Text style={styles.statLabel}>Tasks</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Recent Alerts</Text>
        {alerts.slice(0, 3).map(alert => (
          <View key={alert.id} style={styles.alertCard}>
            <View style={[styles.alertDot, { backgroundColor: getAlertColor(alert.severity) }]} />
            <View style={styles.alertContent}>
              <Text style={styles.alertTitle}>{alert.title}</Text>
              <Text style={styles.alertMessage}>{alert.message}</Text>
              <Text style={styles.alertTime}>{formatTime(alert.timestamp)}</Text>
            </View>
          </View>
        ))}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Active Projects</Text>
        {projects
          .filter(project => project.status === 'active')
          .map(project => (
            <TouchableOpacity
              key={project.id}
              style={styles.projectCard}
              onPress={() => {
                setCurrentScreen('project');
              }}
            >
              <Text style={styles.projectName}>{project.name}</Text>
              <Text style={styles.projectDescription}>{project.description}</Text>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${project.progress}%` }]} />
              </View>
              <Text style={styles.progressText}>{project.progress}% Complete</Text>
            </TouchableOpacity>
          ))}
      </View>
    </ScrollView>
  );

  const renderChatScreen = () => (
    <View style={styles.chatContainer}>
      <ScrollView
        ref={chatScrollRef}
        style={styles.chatMessages}
        onContentSizeChange={() => chatScrollRef.current?.scrollToEnd()}
      >
        {chatMessages.map(msg => (
          <View
            key={msg.id}
            style={[styles.messageContainer, msg.role === 'user' ? styles.userMessage : styles.aiMessage]}
          >
            <Text style={styles.messageText}>{msg.content}</Text>
            <Text style={styles.messageTime}>{formatTime(msg.timestamp)}</Text>
          </View>
        ))}

        {isAITyping && (
          <View style={[styles.messageContainer, styles.aiMessage]}>
            <ActivityIndicator color={COLORS.primary} />
            <Text style={styles.typingText}>AI is thinking...</Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.chatInputContainer}>
        <TextInput
          style={styles.chatInput}
          placeholder="Ask AI anything..."
          value={messageInput}
          onChangeText={setMessageInput}
          multiline
        />
        <TouchableOpacity
          style={styles.sendButton}
          onPress={sendMessage}
          disabled={!messageInput.trim() || !isOnline}
        >
          <Text style={styles.sendButtonText}>➤</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderAlertsScreen = () => (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.screenTitle}>Alerts & Notifications</Text>
      {alerts.map(alert => (
        <View key={alert.id} style={styles.alertCard}>
          <View style={[styles.alertDot, { backgroundColor: getAlertColor(alert.severity) }]} />
          <View style={styles.alertContent}>
            <Text style={styles.alertTitle}>{alert.title}</Text>
            <Text style={styles.alertMessage}>{alert.message}</Text>
            <Text style={styles.alertTime}>{formatTime(alert.timestamp)}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );

  const renderTasksScreen = () => (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.screenTitle}>My Tasks</Text>
      {tasks.map(task => (
        <View key={task.id} style={styles.taskCard}>
          <View style={styles.taskHeader}>
            <Text style={styles.taskTitle}>{task.title}</Text>
            <View style={[styles.priorityBadge, getPriorityStyle(task.priority)]}>
              <Text style={styles.priorityText}>{task.priority}</Text>
            </View>
          </View>
          <Text style={styles.taskDescription}>{task.description}</Text>
          <Text style={styles.taskDueDate}>Due: {formatDate(task.due_date)}</Text>
        </View>
      ))}
    </ScrollView>
  );

  // =====================================================
  // RENDER PHOTO MODAL
  // =====================================================

  const renderPhotoModal = () => (
    <Modal visible={showPhotoModal} animationType="slide" transparent>
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Upload Site Photo</Text>

          {selectedPhoto && <Image source={{ uri: selectedPhoto.uri }} style={styles.photoPreview} />}

          <TextInput
            style={styles.modalInput}
            placeholder="Add description..."
            value={photoDescription}
            onChangeText={setPhotoDescription}
            multiline
            numberOfLines={3}
          />

          <View style={styles.modalButtons}>
            <TouchableOpacity
              style={[styles.modalButton, styles.cancelButton]}
              onPress={() => {
                setShowPhotoModal(false);
                setSelectedPhoto(null);
                setPhotoDescription('');
              }}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.modalButton, styles.uploadButton]}
              onPress={() => uploadPhoto(photoDescription)}
              disabled={isLoading}
            >
              {isLoading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.uploadButtonText}>Upload</Text>}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  // =====================================================
  // BOTTOM NAVIGATION
  // =====================================================

  const renderBottomNav = () => (
    <View style={styles.bottomNav}>
      <TouchableOpacity style={styles.navItem} onPress={() => setCurrentScreen('home')}>
        <Text style={[styles.navIcon, currentScreen === 'home' && styles.navIconActive]}>🏠</Text>
        <Text style={[styles.navLabel, currentScreen === 'home' && styles.navLabelActive]}>Home</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.navItem} onPress={() => setCurrentScreen('chat')}>
        <Text style={[styles.navIcon, currentScreen === 'chat' && styles.navIconActive]}>💬</Text>
        <Text style={[styles.navLabel, currentScreen === 'chat' && styles.navLabelActive]}>AI Chat</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.navItem} onPress={capturePhoto}>
        <View style={styles.cameraButton}>
          <Text style={styles.cameraIcon}>📷</Text>
        </View>
      </TouchableOpacity>

      <TouchableOpacity style={styles.navItem} onPress={() => setCurrentScreen('alerts')}>
        <Text style={[styles.navIcon, currentScreen === 'alerts' && styles.navIconActive]}>🔔</Text>
        {alerts.length > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{alerts.length}</Text>
          </View>
        )}
        <Text style={[styles.navLabel, currentScreen === 'alerts' && styles.navLabelActive]}>Alerts</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.navItem} onPress={() => setCurrentScreen('tasks')}>
        <Text style={[styles.navIcon, currentScreen === 'tasks' && styles.navIconActive]}>✓</Text>
        <Text style={[styles.navLabel, currentScreen === 'tasks' && styles.navLabelActive]}>Tasks</Text>
      </TouchableOpacity>
    </View>
  );

  // =====================================================
  // UTILITY FUNCTIONS
  // =====================================================

  const formatTime = date => {
    const parsedDate = new Date(date);
    return parsedDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = date => {
    const parsedDate = new Date(date);
    return parsedDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getAlertColor = severity => {
    switch (severity) {
      case 'critical':
        return COLORS.danger;
      case 'high':
        return COLORS.warning;
      case 'medium':
        return COLORS.accent;
      default:
        return COLORS.success;
    }
  };

  const getPriorityStyle = priority => {
    switch (priority) {
      case 'high':
        return { backgroundColor: '#FEE2E2', borderColor: COLORS.danger };
      case 'medium':
        return { backgroundColor: '#FEF3C7', borderColor: COLORS.warning };
      default:
        return { backgroundColor: '#D1FAE5', borderColor: COLORS.success };
    }
  };

  // =====================================================
  // MAIN RENDER
  // =====================================================

  if (!isLoggedIn) {
    return renderLoginScreen();
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />

      <View style={styles.content}>
        {currentScreen === 'home' && renderHomeScreen()}
        {currentScreen === 'chat' && renderChatScreen()}
        {currentScreen === 'alerts' && renderAlertsScreen()}
        {currentScreen === 'tasks' && renderTasksScreen()}
      </View>

      {renderBottomNav()}

      {renderPhotoModal()}

      {isLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color={COLORS.primary} />
        </View>
      )}
    </SafeAreaView>
  );
};

// =====================================================
// STYLES
// =====================================================

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.background
  },
  content: {
    flex: 1
  },
  container: {
    flex: 1,
    backgroundColor: COLORS.background
  },
  loginContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: COLORS.background
  },
  loginCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: COLORS.card,
    borderRadius: 20,
    padding: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5
  },
  loginTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.primary,
    textAlign: 'center',
    marginBottom: 8
  },
  loginSubtitle: {
    fontSize: 16,
    color: COLORS.textLight,
    textAlign: 'center',
    marginBottom: 30
  },
  input: {
    backgroundColor: COLORS.background,
    borderRadius: 12,
    padding: 15,
    marginBottom: 15,
    fontSize: 16,
    borderWidth: 1,
    borderColor: COLORS.border
  },
  loginButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 10
  },
  loginButtonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '600'
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 10
  },
  headerTitle: {
    fontSize: 16,
    color: COLORS.textLight
  },
  headerName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.text
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20
  },
  online: {
    backgroundColor: '#D1FAE5'
  },
  offline: {
    backgroundColor: '#FEE2E2'
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600'
  },
  statsContainer: {
    flexDirection: 'row',
    padding: 20,
    paddingTop: 10,
    gap: 10
  },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3
  },
  statNumber: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginBottom: 4
  },
  statLabel: {
    fontSize: 12,
    color: COLORS.textLight
  },
  section: {
    padding: 20,
    paddingTop: 10
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 15
  },
  screenTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: COLORS.text,
    padding: 20,
    paddingBottom: 10
  },
  alertCard: {
    flexDirection: 'row',
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2
  },
  alertDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    marginRight: 12
  },
  alertContent: {
    flex: 1
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 4
  },
  alertMessage: {
    fontSize: 14,
    color: COLORS.textLight,
    marginBottom: 4
  },
  alertTime: {
    fontSize: 12,
    color: COLORS.textLight
  },
  projectCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3
  },
  projectName: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 4
  },
  projectDescription: {
    fontSize: 14,
    color: COLORS.textLight,
    marginBottom: 12
  },
  progressBar: {
    height: 6,
    backgroundColor: COLORS.background,
    borderRadius: 3,
    marginBottom: 6,
    overflow: 'hidden'
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 3
  },
  progressText: {
    fontSize: 12,
    color: COLORS.textLight
  },
  taskCard: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    marginHorizontal: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3
  },
  taskHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.text,
    flex: 1
  },
  priorityBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1
  },
  priorityText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase'
  },
  taskDescription: {
    fontSize: 14,
    color: COLORS.textLight,
    marginBottom: 8
  },
  taskDueDate: {
    fontSize: 12,
    color: COLORS.textLight
  },
  chatContainer: {
    flex: 1,
    backgroundColor: COLORS.background
  },
  chatMessages: {
    flex: 1,
    padding: 20
  },
  messageContainer: {
    maxWidth: '80%',
    borderRadius: 16,
    padding: 12,
    marginBottom: 12
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: COLORS.primary
  },
  aiMessage: {
    alignSelf: 'flex-start',
    backgroundColor: COLORS.card,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2
  },
  messageText: {
    fontSize: 15,
    color: COLORS.text,
    lineHeight: 20
  },
  messageTime: {
    fontSize: 11,
    color: COLORS.textLight,
    marginTop: 4
  },
  typingText: {
    fontSize: 14,
    color: COLORS.textLight,
    marginLeft: 8
  },
  chatInputContainer: {
    flexDirection: 'row',
    padding: 15,
    backgroundColor: COLORS.card,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    alignItems: 'center'
  },
  chatInput: {
    flex: 1,
    backgroundColor: COLORS.background,
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 100,
    marginRight: 10
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center'
  },
  sendButtonText: {
    fontSize: 20,
    color: '#FFF'
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  modalContent: {
    width: '100%',
    backgroundColor: COLORS.card,
    borderRadius: 20,
    padding: 20
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: COLORS.text,
    marginBottom: 15
  },
  photoPreview: {
    width: '100%',
    height: 250,
    borderRadius: 12,
    marginBottom: 15
  },
  modalInput: {
    backgroundColor: COLORS.background,
    borderRadius: 12,
    padding: 12,
    fontSize: 15,
    marginBottom: 15,
    minHeight: 80,
    textAlignVertical: 'top'
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 10
  },
  modalButton: {
    flex: 1,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center'
  },
  cancelButton: {
    backgroundColor: COLORS.background
  },
  cancelButtonText: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: '600'
  },
  uploadButton: {
    backgroundColor: COLORS.primary
  },
  uploadButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600'
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: COLORS.card,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingBottom: Platform.OS === 'ios' ? 20 : 10,
    paddingTop: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 10
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center'
  },
  navIcon: {
    fontSize: 24,
    marginBottom: 4,
    opacity: 0.5
  },
  navIconActive: {
    opacity: 1
  },
  navLabel: {
    fontSize: 11,
    color: COLORS.textLight
  },
  navLabelActive: {
    color: COLORS.primary,
    fontWeight: '600'
  },
  cameraButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: -20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8
  },
  cameraIcon: {
    fontSize: 28
  },
  badge: {
    position: 'absolute',
    top: 0,
    right: '25%',
    backgroundColor: COLORS.danger,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center'
  },
  badgeText: {
    color: '#FFF',
    fontSize: 11,
    fontWeight: 'bold'
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    justifyContent: 'center',
    alignItems: 'center'
  }
});

export default DiriyahMobileApp;
