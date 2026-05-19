package com.atakmap.android.meshtastic.util;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;

import androidx.core.app.NotificationCompat;

import com.atakmap.android.meshtastic.plugin.R;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class NotificationHelperTest {

    @Mock
    private Context context;

    @Mock
    private Context applicationContext;

    @Mock
    private NotificationManager notificationManager;

    private NotificationHelper notificationHelper;

    @BeforeEach
    void setUp() {
        when(context.getApplicationContext()).thenReturn(applicationContext);
        when(applicationContext.getSystemService(Context.NOTIFICATION_SERVICE))
                .thenReturn(notificationManager);
        
        // Clear singleton instance for each test
        try {
            java.lang.reflect.Field instance = NotificationHelper.class.getDeclaredField("instance");
            instance.setAccessible(true);
            instance.set(null, null);
        } catch (Exception e) {
            // Ignore reflection errors in test
        }
        
        notificationHelper = NotificationHelper.getInstance(context);
    }

    @Test
    void shouldUseSingletonPattern() {
        // When
        NotificationHelper instance1 = NotificationHelper.getInstance(context);
        NotificationHelper instance2 = NotificationHelper.getInstance(context);
        
        // Then
        assertThat(instance1).isSameAs(instance2);
    }

    @Test
    void shouldCreateNotificationChannel() {
        // Given
        ArgumentCaptor<NotificationChannel> channelCaptor = 
                ArgumentCaptor.forClass(NotificationChannel.class);
        
        // When - Already created in setUp via getInstance
        
        // Then
        verify(notificationManager).createNotificationChannel(channelCaptor.capture());
        NotificationChannel channel = channelCaptor.getValue();
        assertThat(channel.getId()).isEqualTo(Constants.NOTIFICATION_CHANNEL_ID);
        assertThat(channel.getName().toString()).isEqualTo(Constants.NOTIFICATION_CHANNEL_NAME);
        assertThat(channel.getImportance()).isEqualTo(NotificationManager.IMPORTANCE_DEFAULT);
    }

    @Test
    void shouldShowProgressNotification() {
        // Given
        int progress = 50;
        ArgumentCaptor<Notification> notificationCaptor = 
                ArgumentCaptor.forClass(Notification.class);
        
        // When
        notificationHelper.showProgressNotification(progress);
        
        // Then
        verify(notificationManager).notify(eq(Constants.NOTIFICATION_ID), 
                notificationCaptor.capture());
        // We can't easily verify the progress value without accessing internal builder state
        // but we can verify the notification was sent
        assertThat(notificationCaptor.getValue()).isNotNull();
    }

    @Test
    void shouldShowCompletionNotification() {
        // Given
        ArgumentCaptor<Notification> notificationCaptor = 
                ArgumentCaptor.forClass(Notification.class);
        
        // When
        notificationHelper.showCompletionNotification();
        
        // Then
        verify(notificationManager).notify(eq(Constants.NOTIFICATION_ID), 
                notificationCaptor.capture());
        assertThat(notificationCaptor.getValue()).isNotNull();
    }

    @Test
    void shouldShowCustomNotification() {
        // Given
        String title = "Test Title";
        String message = "Test Message";
        ArgumentCaptor<Notification> notificationCaptor = 
                ArgumentCaptor.forClass(Notification.class);
        
        // When
        notificationHelper.showNotification(title, message);
        
        // Then
        verify(notificationManager).notify(eq(Constants.NOTIFICATION_ID), 
                notificationCaptor.capture());
        Notification notification = notificationCaptor.getValue();
        assertThat(notification).isNotNull();
        // Verify basic properties that are accessible
        assertThat(notification.getSmallIcon().getResId()).isEqualTo(R.drawable.ic_launcher);
    }

    @Test
    void shouldCancelNotification() {
        // When
        notificationHelper.cancelNotification();
        
        // Then
        verify(notificationManager).cancel(Constants.NOTIFICATION_ID);
    }

    @Test
    void shouldShowMultipleProgressUpdates() {
        // When
        notificationHelper.showProgressNotification(25);
        notificationHelper.showProgressNotification(50);
        notificationHelper.showProgressNotification(75);
        notificationHelper.showProgressNotification(100);
        
        // Then
        verify(notificationManager, times(4)).notify(eq(Constants.NOTIFICATION_ID), 
                any(Notification.class));
    }

    @Test
    void shouldTransitionFromProgressToCompletion() {
        // When
        notificationHelper.showProgressNotification(50);
        notificationHelper.showCompletionNotification();
        
        // Then
        verify(notificationManager, times(2)).notify(eq(Constants.NOTIFICATION_ID), 
                any(Notification.class));
    }

    @Test
    void shouldHandleMultipleNotificationTypes() {
        // When
        notificationHelper.showProgressNotification(30);
        notificationHelper.showNotification("Alert", "New message");
        notificationHelper.showCompletionNotification();
        notificationHelper.cancelNotification();
        
        // Then
        verify(notificationManager, times(3)).notify(eq(Constants.NOTIFICATION_ID), 
                any(Notification.class));
        verify(notificationManager).cancel(Constants.NOTIFICATION_ID);
    }

    @Test
    void shouldInitializeWithProperPendingIntent() {
        // Given - The initialization happens in setUp
        ArgumentCaptor<Intent> intentCaptor = ArgumentCaptor.forClass(Intent.class);
        
        try (MockedStatic<PendingIntent> pendingIntentMockedStatic = 
                Mockito.mockStatic(PendingIntent.class)) {
            
            PendingIntent mockPendingIntent = mock(PendingIntent.class);
            pendingIntentMockedStatic.when(() -> 
                PendingIntent.getActivity(any(Context.class), anyInt(), 
                        intentCaptor.capture(), anyInt()))
                    .thenReturn(mockPendingIntent);
            
            // Re-initialize to capture the intent
            NotificationHelper.getInstance(context);
            
            // Then verify the intent properties
            Intent capturedIntent = intentCaptor.getValue();
            assertThat(capturedIntent).isNotNull();
            assertThat(capturedIntent.getComponent().getPackageName())
                    .isEqualTo(Constants.ATAK_PACKAGE);
            assertThat(capturedIntent.getComponent().getClassName())
                    .isEqualTo(Constants.ATAK_ACTIVITY);
            assertThat(capturedIntent.getFlags())
                    .isEqualTo(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        }
    }
}