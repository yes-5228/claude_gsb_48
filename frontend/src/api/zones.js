import http, { toParams } from './client.js'

// ---- 片区 ----
export const listZones = (params) => http.get('/zones', { params: toParams(params) })
export const getZone = (id) => http.get(`/zones/${id}`)
export const createZone = (payload) => http.post('/zones', payload)
export const updateZone = (id, payload) => http.put(`/zones/${id}`, payload)
export const deleteZone = (id) => http.delete(`/zones/${id}`)
export const zoneOptions = () => http.get('/zones/options')
export const assignStations = (payload) => http.post('/zones/assign-stations', payload)

// ---- 片区责任人任职关系(含历史流水) ----
export const addZoneManager = (zoneId, payload) =>
  http.post(`/zones/${zoneId}/managers`, payload)
export const changeZoneManagerRole = (zoneId, personId, payload) =>
  http.put(`/zones/${zoneId}/managers/${personId}`, payload)
export const removeZoneManager = (zoneId, personId, params = {}) =>
  http.delete(`/zones/${zoneId}/managers/${personId}`, { params: toParams(params) })

// ---- 责任人台账 ----
export const listPersons = (params) => http.get('/persons', { params: toParams(params) })
export const getPerson = (id) => http.get(`/persons/${id}`)
export const createPerson = (payload) => http.post('/persons', payload)
export const updatePerson = (id, payload) => http.put(`/persons/${id}`, payload)
export const deletePerson = (id) => http.delete(`/persons/${id}`)
export const personOptions = () => http.get('/persons/options')
