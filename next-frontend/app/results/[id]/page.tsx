"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getTestResultById, TestResult } from "@/lib/api";
import {
  Container,
  Paper,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

function safeNumber(value: number | null | undefined, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function formatNumber(value: number | null | undefined, digits = 1) {
  return safeNumber(value).toFixed(digits);
}

export default function ResultDetailPage() {
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const resultId = params?.id as string;

  const [result, setResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!token || !user) {
      setLoading(false);
      router.replace("/login");
      return;
    }
    if (!resultId) {
      setLoading(false);
      return;
    }

    const fetchResult = async () => {
      try {
        setLoading(true);
        const data = await getTestResultById(resultId, token);
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load result");
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [authLoading, token, user, resultId, router]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-IN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatTime = (seconds: number) => {
    const safeSeconds = safeNumber(seconds);
    const hours = Math.floor(safeSeconds / 3600);
    const mins = Math.floor((safeSeconds % 3600) / 60);
    const secs = safeSeconds % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m ${secs}s`;
    }
    return `${mins}m ${secs}s`;
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!result) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Test result not found</Alert>
      </Container>
    );
  }

  const resultPercentage = safeNumber(result.percentage);
  const accuracyColor = resultPercentage >= 70 ? "#4caf50" : resultPercentage >= 50 ? "#ff9800" : "#f44336";

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => router.back()}
        sx={{ mb: 2 }}
      >
        Back
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Header */}
      <Paper sx={{ p: 3, mb: 3, backgroundColor: "#f5f5f5" }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 600 }}>
          {result.test_name}
        </Typography>
        <Typography color="textSecondary">{formatDate(result.attempted_at)}</Typography>
      </Paper>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="textSecondary" gutterBottom>
                Score
              </Typography>
              <Typography
                variant="h5"
                sx={{ fontWeight: 600, color: accuracyColor }}
              >
                {result.correct_answers}/{result.total_questions}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="textSecondary" gutterBottom>
                Accuracy
              </Typography>
              <Typography
                variant="h5"
                sx={{ fontWeight: 600, color: accuracyColor }}
              >
                {formatNumber(result.percentage)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={resultPercentage}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="textSecondary" gutterBottom>
                Time Taken
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {formatTime(result.time_taken_seconds)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography color="textSecondary" gutterBottom>
                Total Points
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                {formatNumber(result.score, 2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Question Breakdown */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
          Question Breakdown
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ p: 2, backgroundColor: "#e8f5e9", borderRadius: 1 }}>
              <Typography color="textSecondary" variant="body2">
                Correct
              </Typography>
              <Typography variant="h5" sx={{ color: "#4caf50", fontWeight: 600 }}>
                {result.correct_answers}
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ p: 2, backgroundColor: "#ffebee", borderRadius: 1 }}>
              <Typography color="textSecondary" variant="body2">
                Wrong
              </Typography>
              <Typography variant="h5" sx={{ color: "#f44336", fontWeight: 600 }}>
                {result.wrong_answers}
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ p: 2, backgroundColor: "#fff3e0", borderRadius: 1 }}>
              <Typography color="textSecondary" variant="body2">
                Unattempted
              </Typography>
              <Typography variant="h5" sx={{ color: "#ff9800", fontWeight: 600 }}>
                {result.unattempted_questions}
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Box sx={{ p: 2, backgroundColor: "#f3e5f5", borderRadius: 1 }}>
              <Typography color="textSecondary" variant="body2">
                Total
              </Typography>
              <Typography variant="h5" sx={{ color: "#9c27b0", fontWeight: 600 }}>
                {result.total_questions}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Subject Performance */}
      {result.subjects && result.subjects.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Subject-wise Performance
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead sx={{ backgroundColor: "#f5f5f5" }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Subject</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    Score
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    Correct
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    Wrong
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    Total Questions
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 600 }}>
                    Accuracy
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {result.subjects.map((subject) => (
                  <TableRow key={subject.id}>
                    <TableCell>{subject.subject_name}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatNumber(subject.score, 2)}
                    </TableCell>
                    <TableCell align="right" sx={{ color: "#4caf50" }}>
                      {subject.correct_answers}
                    </TableCell>
                    <TableCell align="right" sx={{ color: "#f44336" }}>
                      {subject.wrong_answers}
                    </TableCell>
                    <TableCell align="right">{subject.total_questions}</TableCell>
                    <TableCell
                      align="right"
                      sx={{
                        fontWeight: 600,
                        color: safeNumber(subject.percentage) >= 70 ? "#4caf50" : "#ff9800",
                      }}
                    >
                      {formatNumber(subject.percentage)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Container>
  );
}
