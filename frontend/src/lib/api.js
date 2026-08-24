import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const createRoom = (name) => api.post("/rooms", { name }).then((r) => r.data);
export const joinRoom = (code, name) => api.post(`/rooms/${code}/join`, { name }).then((r) => r.data);
export const getPuzzle = (code) => api.get(`/rooms/${code}/puzzle`).then((r) => r.data);
export const getState = (code, playerId) =>
  api.get(`/rooms/${code}/state`, { params: { player_id: playerId } }).then((r) => r.data);
export const setCell = (code, playerId, row, col, letter) =>
  api.post(`/rooms/${code}/cell`, { player_id: playerId, row, col, letter }).then((r) => r.data);
export const setFocus = (code, playerId, row, col, direction) =>
  api.post(`/rooms/${code}/focus`, { player_id: playerId, row, col, direction }).then((r) => r.data);
export const newPuzzle = (code) => api.post(`/rooms/${code}/new`).then((r) => r.data);
