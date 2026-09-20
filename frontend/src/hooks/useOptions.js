import { useCallback } from 'react'
import { personOptions as fetchPersonOptions, zoneOptions as fetchZoneOptions } from '../api/zones.js'
import { pollutants as fetchPollutants } from '../api/meta.js'
import { stationOptions as fetchStationOptions } from '../api/stations.js'
import { useAsyncData } from './useAsyncData.js'

/** Module level promise cache: options are stable, avoid refetching on every route change. */
let stationCache = null
let pollutantCache = null
let zoneCache = null
let personCache = null

export function useStationOptions() {
  const loader = useCallback(async () => {
    if (!stationCache) {
      stationCache = fetchStationOptions().catch((error) => {
        stationCache = null
        throw error
      })
    }
    return stationCache
  }, [])
  return useAsyncData(loader)
}

export function usePollutantMeta() {
  const loader = useCallback(async () => {
    if (!pollutantCache) {
      pollutantCache = fetchPollutants().catch((error) => {
        pollutantCache = null
        throw error
      })
    }
    return pollutantCache
  }, [])
  return useAsyncData(loader)
}

export function useZoneOptions() {
  const loader = useCallback(async () => {
    if (!zoneCache) {
      zoneCache = fetchZoneOptions().catch((error) => {
        zoneCache = null
        throw error
      })
    }
    return zoneCache
  }, [])
  return useAsyncData(loader)
}

export function usePersonOptions() {
  const loader = useCallback(async () => {
    if (!personCache) {
      personCache = fetchPersonOptions().catch((error) => {
        personCache = null
        throw error
      })
    }
    return personCache
  }, [])
  return useAsyncData(loader)
}

export function resetOptionCache() {
  stationCache = null
  pollutantCache = null
  zoneCache = null
  personCache = null
}
