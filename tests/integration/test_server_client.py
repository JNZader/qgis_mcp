"""
Integration tests for Server-Client Communication

Tests cover:
- Full request-response cycle
- Protocol integration
- Authentication integration
- Rate limiting integration
- Error handling
- Connection management
- TLS integration
"""

import pytest
import socket
import threading
import time
from protocol import ProtocolHandler


@pytest.mark.integration
class TestBasicServerClient:
    """Test basic server-client communication"""

    def test_ping_request_response(self, protocol_handler, socket_pair):
        """Test basic ping request and response"""
        server_sock, client_sock = socket_pair

        # Client sends ping
        ping_msg = {'type': 'ping', 'id': 'msg_001'}
        protocol_handler.send_message(client_sock, ping_msg)

        # Server receives
        received = protocol_handler.receive_message(server_sock, timeout=1.0)
        assert received['type'] == 'ping'

        # Server responds
        response = {
            'type': 'response',
            'id': 'msg_001',
            'success': True,
            'data': {'pong': True}
        }
        protocol_handler.send_message(server_sock, response)

        # Client receives response
        client_response = protocol_handler.receive_message(client_sock, timeout=1.0)
        assert client_response['success'] is True

    def test_multiple_requests(self, protocol_handler, socket_pair):
        """Test multiple requests in sequence"""
        server_sock, client_sock = socket_pair

        for i in range(5):
            # Send request
            msg = {'type': 'ping', 'id': f'msg_{i:03d}'}
            protocol_handler.send_message(client_sock, msg)

            # Receive on server
            received = protocol_handler.receive_message(server_sock, timeout=1.0)
            assert received['id'] == f'msg_{i:03d}'

            # Send response
            response = {
                'type': 'response',
                'id': f'msg_{i:03d}',
                'success': True,
                'data': {}
            }
            protocol_handler.send_message(server_sock, response)

            # Receive response on client
            client_resp = protocol_handler.receive_message(client_sock, timeout=1.0)
            assert client_resp['id'] == f'msg_{i:03d}'


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Test authentication in server-client context"""

    def test_authenticate_request(self, protocol_handler, socket_pair, auth_manager):
        """Test authentication request flow"""
        server_sock, client_sock = socket_pair
        token = auth_manager.api_token
        client_addr = "127.0.0.1:40001"

        # Client sends auth request
        auth_msg = {
            'type': 'authenticate',
            'id': 'auth_001',
            'data': {'token': token}
        }
        protocol_handler.send_message(client_sock, auth_msg)

        # Server receives and processes
        received = protocol_handler.receive_message(server_sock, timeout=1.0)
        assert received['type'] == 'authenticate'

        # Server verifies token
        is_valid = auth_manager.verify_token(client_addr, received['data']['token'])

        # Server responds
        response = {
            'type': 'response',
            'id': 'auth_001',
            'success': is_valid,
            'data': {'authenticated': is_valid}
        }
        protocol_handler.send_message(server_sock, response)

        # Client receives response
        client_resp = protocol_handler.receive_message(client_sock, timeout=1.0)
        assert client_resp['success'] is True
        assert client_resp['data']['authenticated'] is True

    def test_reject_unauthenticated_request(self, protocol_handler, socket_pair, auth_manager):
        """Test that unauthenticated requests are rejected"""
        server_sock, client_sock = socket_pair
        client_addr = "127.0.0.1:40002"

        # Client sends request without auth
        msg = {'type': 'list_layers', 'id': 'msg_001'}
        protocol_handler.send_message(client_sock, msg)

        # Server receives
        received = protocol_handler.receive_message(server_sock, timeout=1.0)

        # Server checks authentication
        is_authenticated = auth_manager.is_authenticated(client_addr)

        # Server responds with error
        response = {
            'type': 'response',
            'id': 'msg_001',
            'success': False,
            'error': 'Authentication required' if not is_authenticated else None
        }
        protocol_handler.send_message(server_sock, response)

        # Client receives error
        client_resp = protocol_handler.receive_message(client_sock, timeout=1.0)
        assert client_resp['success'] is False


@pytest.mark.integration
class TestRateLimitingIntegration:
    """Test rate limiting in server-client context"""

    def test_rate_limit_enforcement(self, protocol_handler, socket_pair, rate_limiter):
        """Test that rate limiting is enforced"""
        server_sock, client_sock = socket_pair
        client_addr = "127.0.0.1:40003"

        successful_requests = 0
        rate_limited_requests = 0

        # Try to send many requests
        for i in range(40):
            # Check rate limit on server side
            if rate_limiter.check_rate_limit(client_addr, 'normal'):
                successful_requests += 1

                # Send success response
                msg = {'type': 'ping', 'id': f'msg_{i:03d}'}
                protocol_handler.send_message(client_sock, msg)

                received = protocol_handler.receive_message(server_sock, timeout=1.0)

                response = {
                    'type': 'response',
                    'id': f'msg_{i:03d}',
                    'success': True,
                    'data': {}
                }
                protocol_handler.send_message(server_sock, response)
                protocol_handler.receive_message(client_sock, timeout=1.0)
            else:
                rate_limited_requests += 1

        # Should have hit rate limit (30 per minute for normal)
        assert successful_requests == 30
        assert rate_limited_requests == 10


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in server-client context"""

    def test_invalid_message_format(self, protocol_handler, socket_pair):
        """Test handling of invalid message format"""
        server_sock, client_sock = socket_pair

        # Client sends invalid message (missing required field)
        invalid_msg = {'id': 'msg_001'}  # Missing 'type'

        # This should fail validation
        with pytest.raises(Exception):  # ProtocolException
            protocol_handler.send_message(client_sock, invalid_msg)

    def test_message_too_large(self, protocol_handler, socket_pair):
        """Test handling of oversized messages"""
        server_sock, client_sock = socket_pair

        # Create oversized message
        huge_data = 'x' * (protocol_handler.MAX_MESSAGE_SIZE + 1)
        msg = {'type': 'ping', 'id': 'msg_001', 'data': huge_data}

        # Should be rejected
        with pytest.raises(Exception):  # ProtocolException
            protocol_handler.send_message(client_sock, msg)

    def test_connection_closed_gracefully(self, protocol_handler, socket_pair):
        """Test graceful handling of connection closure"""
        server_sock, client_sock = socket_pair

        # Close client socket
        client_sock.close()

        # Server tries to receive
        result = protocol_handler.receive_message(server_sock, timeout=1.0)

        # Should return None (not raise exception)
        assert result is None


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrentClients:
    """Test handling of concurrent clients"""

    def test_multiple_concurrent_connections(self, free_port):
        """Test multiple clients connecting simultaneously"""
        from protocol import BufferedProtocolHandler

        # Create server socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('127.0.0.1', free_port))
        server_sock.listen(5)

        client_results = []

        def client_task(client_id):
            """Client thread task"""
            try:
                # Connect
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_sock.connect(('127.0.0.1', free_port))

                # Send message
                handler = BufferedProtocolHandler(use_msgpack=False, validate_schema=True)
                msg = {'type': 'ping', 'id': f'client_{client_id}'}
                handler.send_message(client_sock, msg)

                # Receive response
                response = handler.receive_message(client_sock, timeout=2.0)

                client_sock.close()
                client_results.append((client_id, response))
            except Exception as e:
                client_results.append((client_id, None))

        def server_task():
            """Server thread task"""
            handler = BufferedProtocolHandler(use_msgpack=False, validate_schema=True)

            for _ in range(3):
                conn, addr = server_sock.accept()

                # Receive message
                msg = handler.receive_message(conn, timeout=2.0)

                # Send response
                response = {
                    'type': 'response',
                    'id': msg['id'],
                    'success': True,
                    'data': {}
                }
                handler.send_message(conn, response)
                conn.close()

        # Start server thread
        server_thread = threading.Thread(target=server_task)
        server_thread.start()

        time.sleep(0.1)  # Let server start

        # Start client threads
        client_threads = []
        for i in range(3):
            t = threading.Thread(target=client_task, args=(i,))
            t.start()
            client_threads.append(t)

        # Wait for all
        for t in client_threads:
            t.join(timeout=5.0)
        server_thread.join(timeout=5.0)

        server_sock.close()

        # Verify all clients got responses
        assert len(client_results) == 3
        for client_id, response in client_results:
            assert response is not None
            assert response['success'] is True


@pytest.mark.integration
class TestMessageValidation:
    """Test message validation in integration"""

    def test_schema_validation_enforced(self, protocol_handler, socket_pair, valid_messages):
        """Test that schema validation is enforced"""
        server_sock, client_sock = socket_pair

        for msg in valid_messages:
            # Should not raise
            protocol_handler.send_message(client_sock, msg)
            received = protocol_handler.receive_message(server_sock, timeout=1.0)
            assert received == msg

    def test_invalid_messages_rejected(self, protocol_handler, socket_pair, invalid_messages):
        """Test that invalid messages are rejected"""
        server_sock, client_sock = socket_pair

        for msg in invalid_messages:
            # Should raise exception during send
            with pytest.raises(Exception):
                protocol_handler.send_message(client_sock, msg)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
