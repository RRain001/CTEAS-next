c-----------------------------------------------------------------------
      program p7t_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7T FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor unit `vwidth` extracted by
c     reference/p7t_source_anchor.f.
c
c --- The elevation grid is supplied per case into /METHD/.
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase nx ny   then nx*ny elevations
c             -> icase dzval then ivalw(k,i,j) for k=1..mxvalz, i fastest
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'methd.puf'
      include 'gridnest.puf'
      include 'grid.puf'
c
      integer mode,ios,icase,nx_i,ny_i,ii,jj,kk,ios2,nn
      real el(400)
      real out(4000)
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7T oracle: missing mode'
c
 10   continue
      read(*,*,iostat=ios) icase,nx_i,ny_i
      if(ios.ne.0) goto 999
      read(*,*,iostat=ios2) (el(nn),nn=1,nx_i*ny_i)
      if(ios2.ne.0) stop 'P7T oracle: missing elevation grid'
      kk=0
      do jj=1,ny_i
      do ii=1,nx_i
         kk=kk+1
         elev(ii,jj,1)=el(kk)
      enddo
      enddo
      nxm(1)=nx_i
      nym(1)=ny_i
      ngrid=1
      nestfac(1)=1.0
      rnxnest0(1)=0.0
      rnynest0(1)=0.0
      call vwidth(.FALSE.)
      kk=0
      do nn=1,mxvalz
      do jj=1,ny_i
      do ii=1,nx_i
         kk=kk+1
         out(kk)=FLOAT(ivalw(nn,ii,jj,1))
      enddo
      enddo
      enddo
      write(*,'(i8,1x,es20.12,4000(1x,es20.12))') icase,dzval,
     &     (out(nn),nn=1,mxvalz*nx_i*ny_i)
      goto 10
c
 999  continue
      end
