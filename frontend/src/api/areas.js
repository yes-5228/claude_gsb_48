import http, { toParams } from './client.js'

// ---- 片区 ----
export const listAreas = (params) => http.get('/areas', { params: toParams(params) })
export const getArea = (id) => http.get(`/areas/${id}`)
export const createArea = (payload) => http.post('/areas', payload)
export const updateArea = (id, payload) => http.put(`/areas/${id}`, payload)
export const areaOptions = () => http.get('/areas/options')
export const areaRanking = (params) => http.get('/areas/ranking', { params: toParams(params) })

// ---- 归属划转与历史 ----
export const assignStations = (payload) => http.post('/areas/assignments', payload)
export const assignmentHistory = (params) =>
  http.get('/areas/history', { params: toParams(params) })

// ---- 责任人 ----
export const listPersons = (params) => http.get('/areas/persons', { params: toParams(params) })
export const getPerson = (id) => http.get(`/areas/persons/${id}`)
export const createPerson = (payload) => http.post('/areas/persons', payload)
export const updatePerson = (id, payload) => http.put(`/areas/persons/${id}`, payload)
export const deletePerson = (id) => http.delete(`/areas/persons/${id}`)
export const personOptions = () => http.get('/areas/persons/options')

// ---- 任职管理 ----
export const addMembership = (payload) => http.post('/areas/memberships', payload)
export const leaveMembership = (id, payload) =>
  http.post(`/areas/memberships/${id}/leave`, payload)
export const membershipHistory = (params) =>
  http.get('/areas/memberships/history', { params: toParams(params) })
