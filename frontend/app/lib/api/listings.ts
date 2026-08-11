import apiClient from './client';
import { Listing, ListingFilterParams } from '@/types/listing';

export async function getListings(params?: ListingFilterParams): Promise<Listing[]> {
  try {
    const response = await apiClient.get('/listings', { params });
    return response.data;
  } catch (error) {
    console.error('Erreur lors du chargement des annonces:', error);
    return [];
  }
}
