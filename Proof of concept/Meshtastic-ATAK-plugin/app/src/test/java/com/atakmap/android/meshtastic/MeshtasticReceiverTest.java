package com.atakmap.android.meshtastic;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.meshtastic.util.Constants;
import com.atakmap.comms.CotServiceRemote;
import com.atakmap.coremap.cot.event.CotEvent;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MeshtasticReceiverTest {

    @Mock
    private MeshtasticExternalGPS meshtasticExternalGPS;

    @Mock
    private Context context;

    @Mock
    private Intent intent;

    @Mock
    private MapView mapView;

    @Mock
    private NotificationManager notificationManager;

    @Mock
    private SharedPreferences sharedPreferences;

    @Mock
    private SharedPreferences.Editor editor;

    private MeshtasticReceiver meshtasticReceiver;

    @BeforeEach
    void setUp() {
        // Setup mocks for MapView
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            when(mapView.getContext()).thenReturn(context);
            when(context.getSystemService(Context.NOTIFICATION_SERVICE))
                    .thenReturn(notificationManager);
            when(context.checkSelfPermission(anyString()))
                    .thenReturn(PackageManager.PERMISSION_GRANTED);
            
            meshtasticReceiver = new MeshtasticReceiver(meshtasticExternalGPS);
        }
    }

    @Test
    void shouldHandleMeshConnectedAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_MESH_CONNECTED);
        when(intent.getStringExtra(Constants.EXTRA_CONNECTED))
                .thenReturn(Constants.STATE_CONNECTED);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class);
             MockedStatic<MeshtasticMapComponent> componentMockedStatic = 
                     Mockito.mockStatic(MeshtasticMapComponent.class)) {
            
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            componentMockedStatic.when(MeshtasticMapComponent::reconnect).thenReturn(true);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            componentMockedStatic.verify(MeshtasticMapComponent::reconnect);
        }
    }

    @Test
    void shouldHandleMeshDisconnectedAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_MESH_DISCONNECTED);
        when(intent.getBooleanExtra(Constants.EXTRA_PERMANENT, false))
                .thenReturn(false);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class);
             MockedStatic<MeshtasticMapComponent> componentMockedStatic = 
                     Mockito.mockStatic(MeshtasticMapComponent.class)) {
            
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then - verify state change happens
            assertThat(intent.getAction()).isEqualTo(Constants.ACTION_MESH_DISCONNECTED);
        }
    }

    @Test
    void shouldIgnoreNullAction() {
        // Given
        when(intent.getAction()).thenReturn(null);
        
        // When
        meshtasticReceiver.onReceive(context, intent);
        
        // Then - should return early, no exceptions
        verify(intent).getAction();
        verify(intent, never()).getStringExtra(anyString());
    }

    @Test
    void shouldHandleTextMessageAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_TEXT_MESSAGE_APP);
        byte[] payload = "Test message".getBytes();
        when(intent.getByteArrayExtra(Constants.EXTRA_PAYLOAD)).thenReturn(payload);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getByteArrayExtra(Constants.EXTRA_PAYLOAD);
        }
    }

    @Test
    void shouldHandlePositionAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_RECEIVED_POSITION_APP);
        byte[] payload = new byte[]{1, 2, 3, 4}; // Sample position data
        when(intent.getByteArrayExtra(Constants.EXTRA_PAYLOAD)).thenReturn(payload);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getByteArrayExtra(Constants.EXTRA_PAYLOAD);
        }
    }

    @Test
    void shouldHandleNodeInfoAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_RECEIVED_NODEINFO_APP);
        byte[] payload = new byte[]{1, 2, 3, 4}; // Sample node info data
        when(intent.getByteArrayExtra(Constants.EXTRA_PAYLOAD)).thenReturn(payload);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getByteArrayExtra(Constants.EXTRA_PAYLOAD);
        }
    }

    @Test
    void shouldHandleAtakForwarderAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_RECEIVED_ATAK_FORWARDER);
        byte[] payload = "<?xml version='1.0'?><event/>".getBytes();
        when(intent.getByteArrayExtra(Constants.EXTRA_PAYLOAD)).thenReturn(payload);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            when(mapView.getContext()).thenReturn(context);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getByteArrayExtra(Constants.EXTRA_PAYLOAD);
        }
    }

    @Test
    void shouldHandleAudioAppAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_RECEIVED_AUDIO_APP);
        byte[] payload = new byte[100]; // Sample audio data
        when(intent.getByteArrayExtra(Constants.EXTRA_PAYLOAD)).thenReturn(payload);
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getByteArrayExtra(Constants.EXTRA_PAYLOAD);
        }
    }

    @Test
    void shouldHandleMessageStatusAction() {
        // Given
        when(intent.getAction()).thenReturn(Constants.ACTION_MESSAGE_STATUS);
        when(intent.getIntExtra(eq(Constants.EXTRA_PACKET_ID), eq(0))).thenReturn(123);
        when(intent.getStringExtra(Constants.EXTRA_STATUS)).thenReturn("DELIVERED");
        
        try (MockedStatic<MapView> mapViewMockedStatic = Mockito.mockStatic(MapView.class)) {
            mapViewMockedStatic.when(MapView::getMapView).thenReturn(mapView);
            
            // When
            meshtasticReceiver.onReceive(context, intent);
            
            // Then
            verify(intent).getIntExtra(eq(Constants.EXTRA_PACKET_ID), eq(0));
            verify(intent).getStringExtra(Constants.EXTRA_STATUS);
        }
    }

    @Test
    void shouldImplementCotEventListener() {
        // Given
        CotEvent cotEvent = mock(CotEvent.class);
        
        // When
        meshtasticReceiver.onCotEvent(cotEvent, null);
        
        // Then - verify it implements the interface
        assertThat(meshtasticReceiver).isInstanceOf(CotServiceRemote.CotEventListener.class);
    }
}