// Placeholder k6 script for load testing /api/vr_chat
import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
  vus: 5,
  duration: '30s',
};

export default function () {
  const url = 'http://localhost:8000/api/vr_chat';
  const payload = JSON.stringify({
    session_id: 'load-test',
    user_text: 'Hello Ailey, this is a load test.',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post(url, payload, params);
  sleep(1);
}
