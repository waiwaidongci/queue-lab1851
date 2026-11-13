import {request} from './client';import {Profile} from '../types/domain';export const getProfiles=()=>request<Profile[]>('/profiles');
