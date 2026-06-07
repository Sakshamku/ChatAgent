"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  getAnalytics,
  getProgress,
  getSubjectPerformance,
  Analytics,
  ProgressDataPoint,
  SubjectPerformance,
} from "@/lib/api";
import {
  Container,
  Paper,
  Box,
  Typography,
  CircularProgress,
  Alert,
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
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import AssignmentIcon from "@mui/icons-material/Assignment";
import TrackChangesIcon from "@mui/icons-material/TrackChanges";

function safeNumber(value: number | null | undefined, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function formatNumber(value: number | null | undefined, digits = 1) {
  return safeNumber(value).toFixed(digits);
}

export default function AnalyticsPage() {
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [progress, setProgress] = useState<ProgressDataPoint[]>([]);
  const [subjectPerformance, setSubjectPerformance] = useState<SubjectPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);

  useEffect(() => {
    function refresh() {
      setRefreshTick((value) => value + 1);
    }
    function handleStorage(event: StorageEvent) {
      if (event.key === "mock-results-updated-at") refresh();
    }

    window.addEventListener("mock-results-updated", refresh);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("mock-results-updated", refresh);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!token || !user) {
      setLoading(false);
      router.replace("/login");
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const [analyticsData, progressData, subjectData] = await Promise.all([
          getAnalytics(token),
          getProgress(token),
          getSubjectPerformance(token),
        ]);
        setAnalytics(analyticsData);
        setProgress(progressData);
        setSubjectPerformance(subjectData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [authLoading, token, user, router, refreshTick]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Analytics Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!analytics || safeNumber(analytics.total_tests) === 0 ? (
        <Paper sx={{ p: 3, textAlign: "center" }}>
          <Typography color="textSecondary">No test data available. Take some tests to see analytics.</Typography>
        </Paper>
      ) : (
        <>
          {/* Key Metrics */}
          <Grid container spacing={2} sx={{ mb: 4 }}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card sx={{ height: "100%", backgroundColor: "#e3f2fd" }}>
                <CardContent sx={{ textAlign: "center" }}>
                  <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                    <AssignmentIcon sx={{ fontSize: 40, color: "#1976d2" }} />
                  </Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Tests
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: "#1976d2" }}>
                    {safeNumber(analytics.total_tests)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card sx={{ height: "100%", backgroundColor: "#f3e5f5" }}>
                <CardContent sx={{ textAlign: "center" }}>
                  <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                    <TrendingUpIcon sx={{ fontSize: 40, color: "#7b1fa2" }} />
                  </Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Average Score
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: "#7b1fa2" }}>
                    {formatNumber(analytics.average_score)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card sx={{ height: "100%", backgroundColor: "#e8f5e9" }}>
                <CardContent sx={{ textAlign: "center" }}>
                  <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                    <EmojiEventsIcon sx={{ fontSize: 40, color: "#388e3c" }} />
                  </Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Best Score
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: "#388e3c" }}>
                    {formatNumber(analytics.best_score)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card sx={{ height: "100%", backgroundColor: "#fff3e0" }}>
                <CardContent sx={{ textAlign: "center" }}>
                  <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                    <TrackChangesIcon sx={{ fontSize: 40, color: "#f57c00" }} />
                  </Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Average Accuracy
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 700, color: "#f57c00" }}>
                    {formatNumber(analytics.average_accuracy)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Detailed Statistics */}
          <Grid container spacing={2} sx={{ mb: 4 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Performance Overview
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                    <Typography color="textSecondary">Average Score</Typography>
                    <Typography sx={{ fontWeight: 600 }}>
                      {formatNumber(analytics.average_score)} / 10
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(safeNumber(analytics.average_score) / 10) * 100}
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                    <Typography color="textSecondary">Best Score</Typography>
                    <Typography sx={{ fontWeight: 600, color: "#388e3c" }}>
                      {formatNumber(analytics.best_score)} / 10
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(safeNumber(analytics.best_score) / 10) * 100}
                    sx={{ backgroundColor: "#e8f5e9", "& .MuiLinearProgress-bar": { backgroundColor: "#388e3c" } }}
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                    <Typography color="textSecondary">Worst Score</Typography>
                    <Typography sx={{ fontWeight: 600, color: "#f44336" }}>
                      {formatNumber(analytics.worst_score)} / 10
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(safeNumber(analytics.worst_score) / 10) * 100}
                    sx={{ backgroundColor: "#ffebee", "& .MuiLinearProgress-bar": { backgroundColor: "#f44336" } }}
                  />
                </Box>

                <Box>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                    <Typography color="textSecondary">Average Accuracy</Typography>
                    <Typography sx={{ fontWeight: 600, color: "#f57c00" }}>
                      {formatNumber(analytics.average_accuracy)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={safeNumber(analytics.average_accuracy)}
                    sx={{ backgroundColor: "#fff3e0", "& .MuiLinearProgress-bar": { backgroundColor: "#f57c00" } }}
                  />
                </Box>
              </Paper>
            </Grid>

            {/* Progress Timeline */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                  Recent Tests
                </Typography>
                {progress.length === 0 ? (
                  <Typography color="textSecondary">No test history available</Typography>
                ) : (
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                    {progress.slice(-5).map((item, idx) => (
                      <Box
                        key={idx}
                        sx={{
                          p: 1.5,
                          backgroundColor: "#f5f5f5",
                          borderRadius: 1,
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {item.test_name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {item.attempted_at}
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: "right" }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {formatNumber(item.score)}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              color: safeNumber(item.percentage) >= 70 ? "#4caf50" : "#ff9800",
                            }}
                          >
                            {formatNumber(item.percentage)}%
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}
              </Paper>
            </Grid>
          </Grid>

          {/* Subject Performance */}
          {subjectPerformance.length > 0 && (
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
                        Avg Accuracy
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        Tests
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        Questions
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        Correct
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {subjectPerformance.map((subject) => (
                      <TableRow key={subject.subject}>
                        <TableCell sx={{ fontWeight: 500 }}>{subject.subject}</TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            fontWeight: 600,
                            color: safeNumber(subject.average_percentage) >= 70 ? "#4caf50" : "#ff9800",
                          }}
                        >
                          {formatNumber(subject.average_percentage)}%
                        </TableCell>
                        <TableCell align="right">{subject.total_tests}</TableCell>
                        <TableCell align="right">{subject.total_questions}</TableCell>
                        <TableCell align="right" sx={{ color: "#4caf50" }}>
                          {subject.total_correct}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}
        </>
      )}
    </Container>
  );
}
